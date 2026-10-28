import {test} from 'node:test';
import assert from 'node:assert/strict';
import {message,assertion,accessToken,send,fcmError} from '../../supabase/functions/aire-push/core.ts';

const job={id:'delivery-test',lease_id:'lease-test',incident_id:'incident-test',classroom_id:'room-test',
 installation_id:'session-binding-test',source:'simulacion',severity:'alerta',token:'fake-device-token-never-send',event_id:'event-test',event_kind:'indicacion'};
test('Contrato Android: simulación, coordinación, acuses cloud y privacidad',()=>{
 const msg=message(job);assert.equal(msg.message.data.channel,'cloud');
 assert.equal(msg.message.data.delivery_id,job.id);assert.equal(msg.message.data.notification_contract,'2');assert.equal(msg.message.data.installation_id,job.installation_id);assert.match(msg.message.data.title,/SIMULACIÓN/);
 assert.match(msg.message.data.title,/Coordinación/);assert.equal(msg.message.android.ttl,'300s');
 assert.ok(Object.values(msg.message.data).every(x=>typeof x==='string'));
 assert.ok(!JSON.stringify(msg).includes('private_key'));
});
test('Clasifica fallas permanentes y reintentables sin registrar mensajes privados',()=>{
 assert.equal(fcmError(404,{error:{details:[{'@type':'type.googleapis.com/google.firebase.fcm.v1.FcmError',errorCode:'UNREGISTERED'}]}}),'UnregisteredError');
 assert.equal(fcmError(403,{}),'FirebaseAuthorizationError');assert.equal(fcmError(500,{}),'FirebaseTemporaryError');
 assert.equal(fcmError(429,{}),'QuotaExceededError');
});
test('Aceptación FCM y error mediante transporte simulado, nunca envío real',async()=>{
 const result=await send(job,'sfa-aire-aulas','fake-access-token',async(url,req)=>{
  assert.equal(url,'https://fcm.googleapis.com/v1/projects/sfa-aire-aulas/messages:send');
  assert.equal(req.headers.Authorization,'Bearer fake-access-token');
  assert.equal(JSON.parse(req.body).message.token,job.token);
  return Response.json({name:'projects/sfa-aire-aulas/messages/MOCK'});
 });
 assert.equal(result.provider,'projects/sfa-aire-aulas/messages/MOCK');assert.equal(result.error,null);
 const failure=await send(job,'sfa-aire-aulas','fake',async()=>Response.json({}, {status:503}));
 assert.equal(failure.error,'FirebaseTemporaryError');
});
test('Firma RS256 y OAuth de cuenta exclusiva con clave efímera de prueba',async()=>{
 const pair=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
 const pem=Buffer.from(await crypto.subtle.exportKey('pkcs8',pair.privateKey)).toString('base64');
 const account={project_id:'sfa-aire-aulas',client_email:'sender@sfa-aire-aulas.iam.gserviceaccount.com',
  private_key:`-----BEGIN PRIVATE KEY-----\n${pem}\n-----END PRIVATE KEY-----`};
 const jwt=await assertion(account,123456);const [header,payload,sig]=jwt.split('.');
 const claims=JSON.parse(Buffer.from(payload,'base64url'));assert.equal(claims.exp-claims.iat,3600);
 assert.equal(claims.scope,'https://www.googleapis.com/auth/firebase.messaging');
 assert.ok(await crypto.subtle.verify('RSASSA-PKCS1-v1_5',pair.publicKey,Buffer.from(sig,'base64url'),new TextEncoder().encode(header+'.'+payload)));
 assert.equal(await accessToken(account,async(url,req)=>{
  assert.equal(url,'https://oauth2.googleapis.com/token');assert.ok(req.body.get('assertion'));
  return Response.json({access_token:'fake-oauth-token'});
 }),'fake-oauth-token');
 await assert.rejects(()=>assertion({...account,project_id:'another-project'}),/incorrecto/);
 await assert.rejects(()=>accessToken(account,async()=>Response.json({error:'invalid_grant'},{status:400})),/FirebaseOAuthError/);
});
let handler;
test('Endpoint: rechaza llamadas públicas sin consultar ni enviar',async()=>{
 globalThis.Deno={env:{get:name=>name==='SUPABASE_URL'?'https://example.invalid':'fake-service-key-never-use'},serve(fn){handler=fn;}};
 await import('../../supabase/functions/aire-push/index.ts');
 assert.equal((await handler(new Request('https://example.invalid',{method:'GET'}))).status,405);
 assert.equal((await handler(new Request('https://example.invalid',{method:'POST'}))).status,401);
});
test('Recorrido completo del worker con OAuth/FCM/SQL simulados y sin aceptar destinatarios del body',async()=>{
 const pair=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
 const pem=Buffer.from(await crypto.subtle.exportKey('pkcs8',pair.privateKey)).toString('base64');
 const account={project_id:'sfa-aire-aulas',client_email:'sender@sfa-aire-aulas.iam.gserviceaccount.com',private_key:`-----BEGIN PRIVATE KEY-----\n${pem}\n-----END PRIVATE KEY-----`};
 const original=globalThis.fetch,calls=[];
 try {
  globalThis.fetch=async(url,req)=>{
   const name=String(url).split('/').pop();calls.push(name);
   if(name==='aire_cloud_open')return Response.json({authorized:true,ready:true,account});
   if(name==='token')return Response.json({access_token:'fake-oauth'});
   if(name==='aire_cloud_health')return Response.json(null);
   if(name==='aire_cloud_claim')return Response.json({jobs:[job]});
   if(name==='messages:send'){
    assert.equal(JSON.parse(req.body).message.token,job.token);
    return Response.json({name:'projects/sfa-aire-aulas/messages/MOCK'});
   }
   if(name==='aire_cloud_finish'){
    const body=JSON.parse(req.body);assert.equal(body.p_lease_id,job.lease_id);
    assert.equal(body.p_provider_id,'projects/sfa-aire-aulas/messages/MOCK');
    return Response.json(null);
   }
   throw new Error('Unexpected simulated URL');
  };
  const response=await handler(new Request('https://example.invalid',{method:'POST',headers:{'x-sfa-worker':'a'.repeat(64)},body:'{"token":"forged-recipient"}'}));
  assert.equal(response.status,200);assert.equal((await response.json()).accepted,1);
  assert.deepEqual(calls,['aire_cloud_open','token','aire_cloud_health','aire_cloud_claim','messages:send','aire_cloud_finish']);
 }finally{globalThis.fetch=original;}
});
test('Credencial de worker rechazada en SQL impide OAuth y reclamación',async()=>{
 const original=globalThis.fetch;let calls=0;
 try {
  globalThis.fetch=async()=>{calls++;return Response.json({authorized:false});};
  const response=await handler(new Request('https://example.invalid',{method:'POST',headers:{'x-sfa-worker':'b'.repeat(64)}}));
  assert.equal(response.status,401);assert.equal(calls,1);
 }finally{globalThis.fetch=original;}
});

test('Un trabajo sin vínculo no llama FCM',async()=>{
 let calls=0;
 await assert.rejects(()=>send({...job,installation_id:undefined},'sfa-aire-aulas','fake',async()=>{calls++;return Response.json({name:'MOCK'});}),/NotificationBindingMissing/);
 assert.equal(calls,0);
});

test('Prueba manual cloud no se presenta como variación física sostenida',()=>{
 const msg=message({...job,event_id:undefined,notification_test:true});
 assert.equal(msg.message.data.title,'Alerta simulada');
 assert.match(msg.message.data.body,/no son mediciones físicas/);
 assert.equal(msg.message.data.test_kind,'cloud_notification');
 assert.ok(Object.values(msg.message.data).every(value=>typeof value==='string'));
});
