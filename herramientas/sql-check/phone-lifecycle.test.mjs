import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {randomUUID as uuid} from 'node:crypto';

const db=await createCloudFixture({through:"20261025200720_harden_phone_lifecycle.sql"});let checks=0;
const owner=uuid(),teacher=uuid(),observer=uuid(),other=uuid();
const device=uuid(),binding=uuid(),rotated=uuid(),teacherDevice=uuid(),observerDevice=uuid();
const token='fake-device-token-never-send-11111';
async function actor(id,role='authenticated'){
 await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role);
}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) v`,args)).rows[0].v;}
async function denied(action){await assert.rejects(action);checks++;}
async function phones(){await db.exec('reset role');return (await db.query('select * from public.aire_phones order by classroom_id,device_id')).rows;}
async function register(room,dev,bound,tok=token){await rpc('aire_register_phone_v2',[room,dev,bound,tok,'Android prueba',true]);}
try {
 await db.query('insert into auth.users values($1,$2),($3,$4),($5,$6),($7,$8)',[owner,'owner@test.invalid',teacher,'teacher@test.invalid',observer,'observer@test.invalid',other,'other@test.invalid']);
 await db.query('insert into public.aire_creators values($1),($2)',[owner,other]);
 await actor(owner);const room=await rpc('aire_create_classroom',['Aula principal','Prueba']);
 await rpc('aire_grant_member',[room,'teacher@test.invalid','docente']);await rpc('aire_grant_member',[room,'observer@test.invalid','observador']);
 const gateway=await rpc('aire_create_gateway',[room,'PC prueba']);
 const extra=await rpc('aire_create_classroom',['Otra aula propia','Prueba']);
 await actor(other);const foreign=await rpc('aire_create_classroom',['Aula ajena','Prueba']);
 await actor(null,'anon');await denied(()=>register(room,device,binding));
 await actor(other);await denied(()=>register(room,device,binding));
 await actor(owner);await register(room,device,binding);
 await actor(teacher);await register(room,teacherDevice,uuid(),'fake-teacher-token-never-send-22222');
 await actor(observer);await register(room,observerDevice,uuid(),'fake-observer-token-never-send-33333');
 assert.equal((await phones()).length,3);checks++;
 await actor(owner);await denied(()=>register(room,uuid(),uuid(),'fake-fourth-token-never-send-44444'));
 const incident=uuid(),delivery=uuid(),lease=uuid();
 await db.exec('reset role');
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,'arduino','alerta',now())",[incident,room,gateway.gateway_id]);
 await db.query("insert into public.aire_deliveries(id,classroom_id,incident_id,user_id,installation_id,severity,lease_id,lease_until) values($1,$2,$3,$4,$5,'alerta',$6,now()+interval '2 minutes')",[delivery,room,incident,owner,binding,lease]);
 // El mismo celular puede sustituir sesión y token aun cuando los tres cupos están ocupados.
 await actor(owner);await register(room,device,rotated,'fake-rotated-token-never-send-55555');
 let rows=await phones();assert.equal(rows.length,3);assert.equal(rows.find(r=>r.device_id===device).installation_id,rotated);checks++;
 const retired=(await db.query('select status,lease_id,lease_until from public.aire_deliveries where id=$1',[delivery])).rows[0];
 assert.deepEqual(retired,{status:'cancelado',lease_id:null,lease_until:null});checks++;
 // Un usuario de otra aula no puede limpiar registros antes de comprobar autorización.
 await actor(other);await denied(()=>register(room,device,uuid(),'fake-rotated-token-never-send-55555'));
 assert.equal((await phones()).find(r=>r.device_id===device).installation_id,rotated);checks++;
 await actor(owner);await denied(()=>register(foreign,device,uuid()));
 for(const args of [
  [room,device,uuid(),null,'Android',true],
  [room,device,uuid(),token,null,true],
  [room,device,uuid(),token,'Android',null],
  [room,device,uuid(),'short','Android',true],
 ])await denied(()=>rpc('aire_register_phone_v2',args));
 assert.equal((await phones()).length,3);checks++;
 // Cambiar de cuenta en el mismo equipo retira al usuario anterior incluso con token rotado.
 await actor(teacher);const teacherBinding=uuid();await register(room,device,teacherBinding,'fake-next-user-token-never-send-66666');
 rows=await phones();assert.equal(rows.length,3);assert.equal(rows.find(r=>r.device_id===device).user_id,teacher);checks++;
 // Reinstalación: token conocido, dispositivo local nuevo; tampoco duplica destinatarios.
 await actor(owner);const reinstall=uuid(),newBinding=uuid();await register(room,reinstall,newBinding,'fake-next-user-token-never-send-66666');
 rows=await phones();assert.equal(rows.length,3);assert.equal(rows.find(r=>r.device_id===reinstall).user_id,owner);checks++;
 // Varias aulas conservan consentimiento propio y comparten la rotación de token de esta sesión.
 await actor(owner);await register(extra,reinstall,newBinding,'fake-next-user-token-never-send-66666');
 await register(room,reinstall,newBinding,'fake-new-token-all-rooms-never-send-77777');
 rows=(await phones()).filter(r=>r.device_id===reinstall);assert.equal(rows.length,2);assert.ok(rows.every(r=>r.token==='fake-new-token-all-rooms-never-send-77777'));checks++;
 // Al iniciar otra sesión se retiran también las otras aulas del vínculo anterior.
 await actor(owner);const finalBinding=uuid();await register(room,reinstall,finalBinding,'fake-new-token-all-rooms-never-send-77777');
 rows=(await phones()).filter(r=>r.device_id===reinstall);assert.equal(rows.length,1);assert.equal(rows[0].installation_id,finalBinding);checks++;
 // Una cuota fallida revierte también cualquier limpieza provisional de registros.
 await actor(owner);const movingDevice=uuid(),movingBinding=uuid();
 await register(extra,movingDevice,movingBinding,'fake-distinct-quota-token-never-send-88888');
 await denied(()=>register(room,movingDevice,uuid(),'fake-distinct-quota-token-never-send-88888'));
 rows=await phones();assert.equal(rows.length,4);assert.equal(rows.find(r=>r.device_id===movingDevice).installation_id,movingBinding);checks++;
 await actor(owner);await rpc('aire_unregister_phone',[movingBinding]);
 // El RPC histórico mantiene dispositivo y vínculo iguales para clientes v1.
 await actor(owner);await rpc('aire_unregister_phone',[finalBinding]);await rpc('aire_register_phone',[room,'legacy-installation',token,'Cliente anterior',false]);
 rows=await phones();const legacy=rows.find(r=>r.installation_id==='legacy-installation');assert.equal(legacy.device_id,'legacy-installation');checks++;
 await actor(owner);await denied(()=>rpc('aire_receipt',[delivery,binding,null]));
 await denied(()=>rpc('aire_receipt',[delivery,binding,'otra-accion']));
 await actor(teacher);await denied(()=>rpc('aire_receipt',[delivery,binding,'abierto']));
 const activeDelivery=uuid(),activeLease=uuid();
 await db.exec('reset role');
 await db.query("insert into public.aire_deliveries(id,classroom_id,incident_id,user_id,installation_id,severity,lease_id,lease_until) values($1,$2,$3,$4,$5,'alerta',$6,now()+interval '2 minutes')",[activeDelivery,room,incident,owner,'legacy-installation',activeLease]);
 await actor(null,'anon');await rpc('aire_finish_push',[gateway.gateway_id,gateway.gateway_secret,activeDelivery,activeLease,'fcm/local-mock',null]);
 await db.exec('reset role');assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[activeDelivery])).rows[0].status,'aceptado_fcm');checks++;
 await actor(owner);await denied(()=>rpc('aire_receipt',[activeDelivery,'legacy-installation',null]));
 await db.exec('reset role');assert.equal((await db.query('select received_at from public.aire_deliveries where id=$1',[activeDelivery])).rows[0].received_at,null);checks++;
 await actor(owner);await rpc('aire_receipt',[activeDelivery,'legacy-installation','recibido']);
 await db.exec('reset role');assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[activeDelivery])).rows[0].status,'recibido_app');checks++;
 // Resultado de transporte exige exactamente proveedor o error, en ambos caminos.
 await actor(null,'anon');
 for(const values of [[null,null],['ok','error'],['',null],[null,'  ']])await denied(()=>rpc('aire_finish_push',[gateway.gateway_id,gateway.gateway_secret,delivery,lease,...values]));
 await actor(null,'service_role');
 for(const values of [[null,null],['ok','error'],['',null],[null,'  ']])await denied(()=>rpc('aire_cloud_finish',[delivery,lease,...values]));
 await denied(()=>rpc('aire_cloud_finish_v06',[delivery,lease,'fake',null]));
 await actor(null,'anon');await denied(()=>rpc('aire_finish_push_v06',[gateway.gateway_id,gateway.gateway_secret,delivery,lease,'fake',null]));
 // Ningún helper nuevo es ejecutable directamente por roles de aplicación.
 await db.exec('reset role');
 for(const role of ['anon','authenticated','service_role']){
  const granted=(await db.query("select count(*)::int n from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='aire_private' and has_function_privilege($1,p.oid,'execute')",[role])).rows[0].n;
  assert.equal(granted,0);checks++;
  const legacyGranted=(await db.query("select count(*)::int n from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname ~ '_v0[0-9]$' and has_function_privilege($1,p.oid,'execute')",[role])).rows[0].n;
  assert.equal(legacyGranted,0);checks++;
 }
 const requests=(await db.query('select count(*)::int n from net.test_requests')).rows[0].n;assert.equal(requests,0);checks++;
 await writeFile(new URL('../../artifacts/phone-lifecycle-sql-report.json',import.meta.url),JSON.stringify({checks,real_cloud_requests:0,real_push_sent:0,scenarios:['quota-preserving session rotation','offline logout and token rotation','account change','reinstall','multi-classroom token refresh','cross-classroom denial','null input denial','legacy RPC','receipt ownership','delivery outcome validation','helper grants']},null,2));
 console.log(`PASS: ${checks} comprobaciones de ciclo de vida y autorización del teléfono; PostgreSQL local, sin FCM.`);
}finally{await db.close();}
