type Config={url:string;publicKey:string;secret:string};
const headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization,apikey,content-type,x-client-info','Access-Control-Allow-Methods':'POST,OPTIONS','Content-Type':'application/json','Cache-Control':'no-store'};
const reply=(status:number,message:string,data={})=>new Response(JSON.stringify({message,...data}),{status,headers});
/** Solamente genera invitaciones tras autorización RPC. No envía correo ni recupera contraseñas existentes. */
export async function handleInvitation(req:Request,config:Config,send:typeof fetch=fetch):Promise<Response>{
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers});
 if(req.method!=='POST')return reply(405,'Método no disponible.');
 const auth=req.headers.get('authorization')||'';
 if(!/^Bearer [A-Za-z0-9_.-]+$/.test(auth))return reply(401,'Inicie sesión.');
 if(!config.url||!config.publicKey||!config.secret)return reply(503,'Invitaciones no configuradas.');
 let body:any;
 try{const reader=req.body?.getReader();if(!reader)return reply(400,'Formulario inválido.');let size=0,text='';const decoder=new TextDecoder();while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>4096){await reader.cancel();return reply(413,'Formulario demasiado grande.')}text+=decoder.decode(part.value,{stream:true})}body=JSON.parse(text+decoder.decode())}catch{return reply(400,'Formulario inválido.')}
 if(!body||Object.keys(body).some(k=>!['classroom_id','email','role'].includes(k))||typeof body.classroom_id!=='string'||!/^[0-9a-f-]{36}$/i.test(body.classroom_id)||typeof body.email!=='string'||body.email.length>254||!['admin','docente','observador'].includes(body.role))return reply(400,'Revise correo, aula y permiso.');
 const rpc=async(name:string,args:unknown)=>{
  const r=await send(config.url+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:config.publicKey,Authorization:auth,'Content-Type':'application/json'},body:JSON.stringify(args),redirect:'error',signal:AbortSignal.timeout(10000)});
  return {ok:r.ok,data:await r.json().catch(()=>null)};
 };
 let reserved:string|null=null;
 try{
  const identity=await send(config.url+'/auth/v1/user',{headers:{apikey:config.publicKey,Authorization:auth},redirect:'error',signal:AbortSignal.timeout(10000)});
  if(!identity.ok)return reply(401,'Inicie sesión nuevamente.');
  const token=Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(token))),b=>b.toString(16).padStart(2,'0')).join('');
  const result=await rpc('aire_invite_create',{p_classroom_id:body.classroom_id,p_email:body.email,p_role:body.role,p_hash:hash});
  if(!result.ok)return reply(409,result.data?.message||'No se pudo generar la invitación.');
  const invite=result.data;reserved=invite.id;
  let authHash='';
  if(invite.activation){
   const r=await send(config.url+'/auth/v1/admin/generate_link',{method:'POST',headers:{apikey:config.secret,Authorization:'Bearer '+config.secret,'Content-Type':'application/json'},body:JSON.stringify({type:'invite',email:invite.email}),redirect:'error',signal:AbortSignal.timeout(10000)});
   const data=await r.json().catch(()=>null);authHash=data?.hashed_token||data?.properties?.hashed_token||'';
   if(!r.ok||!authHash){await rpc('aire_invite_revoke',{p_id:reserved});return reply(409,'No se pudo preparar el alta. Actualice las invitaciones y genere una nueva.');}
  }
  const fragment=new URLSearchParams({invitacion:token,correo:invite.email,...(authHash?{alta:authHash}:{})});
  return reply(200,'Invitación preparada. Comparta el enlace de forma privada.',{id:invite.id,expires_at:invite.expires_at,fragment:fragment.toString(),email_sent:false});
 }catch{if(reserved)await rpc('aire_invite_revoke',{p_id:reserved}).catch(()=>{});return reply(503,'No se pudo completar la invitación. Actualice el listado antes de reintentar.');}
}
