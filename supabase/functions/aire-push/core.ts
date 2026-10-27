// Contrato FCM compartido con Android; no incluye decisiones ni texto privado.
export type Job = {
  id: string; lease_id: string; incident_id: string; classroom_id: string;
  token: string; installation_id: string; source: string; severity: string; lab_run_id?: string;
  causes?: string[]; event_id?: string; event_kind?: string; notification_test?: boolean;
};
export type ServiceAccount = { project_id: string; client_email: string; private_key: string };
const labels: Record<string,string> = {indicacion:'nueva indicación',confirmada:'comprensión confirmada',
  impedimento:'se solicita apoyo',aclaracion:'se solicita aclaración',realizada:'resultado completo',
  parcial:'resultado parcial',coordinacion:'responsable actualizado',atender:'contexto registrado',resolver:'revisión y cierre'};
export function message(job: Job) {
  if(typeof job.installation_id!=='string'||job.installation_id.length<8||job.installation_id.length>120)
    throw new Error('NotificationBindingMissing');
  return {message:{token:job.token, android:{priority:'high',ttl:'300s'},data:{
    notification_contract:'2',installation_id:job.installation_id,channel:'cloud',delivery_id:job.id,incident_id:job.incident_id,classroom_id:job.classroom_id,
    source:job.source,severity:job.severity,lab_run_id:job.lab_run_id||'',causes:(job.causes||[]).join(','),
    event_id:job.event_id||'',event_kind:job.event_kind||'',
    test_kind:job.notification_test?'cloud_notification':'',
    title:(job.source==='simulacion'?'SIMULACIÓN · ':'')+(job.notification_test?'SFA Aire · Prueba de notificación':job.event_id?'SFA Aire · Coordinación':'SFA Aire · Revisar aula'),
    body:job.notification_test?'Aviso de prueba desde la nube. No representa una medición física.':job.event_id?'Cambio de coordinación: '+(labels[job.event_kind||'']||'actualización registrada')+'. Abra la app y verifique la indicación vigente.':
      'Variación sostenida registrada. Abra la app para consultar el aula.'
  }}};
}
const encoder = new TextEncoder();
function base64url(data: Uint8Array) {
  return btoa(String.fromCharCode(...data)).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
}
export async function assertion(account: ServiceAccount, now = Math.floor(Date.now()/1000)) {
  if (account.project_id!=='sfa-aire-aulas' || !account.client_email.endsWith('@sfa-aire-aulas.iam.gserviceaccount.com'))
    throw new Error('Proyecto Firebase incorrecto');
  const header=base64url(encoder.encode(JSON.stringify({alg:'RS256',typ:'JWT'})));
  const payload=base64url(encoder.encode(JSON.stringify({iss:account.client_email,
    scope:'https://www.googleapis.com/auth/firebase.messaging',aud:'https://oauth2.googleapis.com/token',iat:now,exp:now+3600})));
  const pem=account.private_key.replace(/-----[^-]+-----/g,'').replace(/\s/g,'');
  const key=await crypto.subtle.importKey('pkcs8',Uint8Array.from(atob(pem),c=>c.charCodeAt(0)),
    {name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
  const unsigned=header+'.'+payload;
  const signature=await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,encoder.encode(unsigned));
  return unsigned+'.'+base64url(new Uint8Array(signature));
}
export async function accessToken(account: ServiceAccount, fetcher: typeof fetch = fetch) {
  const response=await fetcher('https://oauth2.googleapis.com/token',{method:'POST',
    signal:AbortSignal.timeout(8000),headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion:await assertion(account)})});
  const data=await response.json();
  if (!response.ok || typeof data.access_token!=='string') throw new Error('FirebaseOAuthError');
  return data.access_token as string;
}
export function fcmError(status: number, data: any): string {
  const code=data?.error?.details?.find((x:any)=>x['@type']==='type.googleapis.com/google.firebase.fcm.v1.FcmError')?.errorCode;
  if (code==='UNREGISTERED') return 'UnregisteredError';
  if (code==='SENDER_ID_MISMATCH') return 'SenderIdMismatchError';
  if (status===429) return 'QuotaExceededError';
  if (status===401 || status===403) return 'FirebaseAuthorizationError';
  if (status===400) return 'InvalidMessageError';
  return 'FirebaseTemporaryError';
}
export async function send(job: Job, project: string, token: string, fetcher: typeof fetch = fetch) {
  const response=await fetcher(`https://fcm.googleapis.com/v1/projects/${project}/messages:send`,{
    method:'POST',signal:AbortSignal.timeout(8000),headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},
    body:JSON.stringify(message(job))});
  const data=await response.json();
  return response.ok && typeof data.name==='string'?{provider:data.name,error:null}:{provider:null,error:fcmError(response.status,data)};
}
