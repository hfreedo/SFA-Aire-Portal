import {accessToken,send,type Job} from './core.ts';

// La pasarela JWT se reemplaza por una credencial de worker aleatoria de 256 bits.
// Se verifica en SQL con la clave interna service_role, nunca con datos del body.
const json=(body:unknown,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
async function rpc(name:string,args:unknown) {
  const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
  const response=await fetch(Deno.env.get('SUPABASE_URL')+'/rest/v1/rpc/'+name,{
    method:'POST',signal:AbortSignal.timeout(8000),headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify(args)});
  if (!response.ok) throw new Error('WorkerDatabaseError');
  return response.status===204?null:response.json();
}
Deno.serve(async request=>{
  if(request.method!=='POST') return json({error:'method_not_allowed'},405);
  const secret=request.headers.get('x-sfa-worker')||'';
  if(secret.length!==64) return json({error:'unauthorized'},401);
  try {
    const config=await rpc('aire_cloud_open',{p_worker_secret:secret});
    if(!config.authorized) return json({error:'unauthorized'},401);
    if(!config.ready) return json({state:config.state},503);
    let token:string;
    try { token=await accessToken(config.account); }
    catch {
      await rpc('aire_cloud_health',{p_error:'FirebaseOAuthError'});
      return json({state:'firebase_auth_error'},503);
    }
    await rpc('aire_cloud_health',{p_error:null});
    const result=await rpc('aire_cloud_claim',{});
    const jobs:Job[]=result.jobs;
    let accepted=0,failed=0;
    // Tres tandas de tres envíos como máximo; tiempo menor que el lease de 120 s.
    for(let index=0;index<jobs.length;index+=3) {
      await Promise.all(jobs.slice(index,index+3).map(async job=>{
        let outcome:{provider:string|null,error:string|null};
        try { outcome=await send(job,config.account.project_id,token); }
        catch { outcome={provider:null,error:'FirebaseNetworkError'}; }
        await rpc('aire_cloud_finish',{p_delivery_id:job.id,p_lease_id:job.lease_id,
          p_provider_id:outcome.provider,p_error:outcome.error});
        if(outcome.error) failed++; else accepted++;
      }));
    }
    return json({state:'processed',claimed:jobs.length,accepted,failed});
  } catch {
    // No imprimir errores del proveedor, tokens, claves, cuerpos o destinatarios.
    return json({error:'worker_failed'},503);
  }
});
