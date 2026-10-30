import {createCloudFixture} from './cloud-fixture.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import {randomUUID as uuid} from 'node:crypto';
import assert from 'node:assert/strict';
const db=await createCloudFixture({baseline:true});
const actor=async id=>{await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role authenticated')};
const rpc=async(name,args=[]) => (await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v;
try{
 for(const f of ['20261026000132_gateway_lifecycle_capabilities.sql','20261026091353_simplify_alert_attention.sql'])await db.exec(await readFile(new URL('../../supabase/migrations/'+f,import.meta.url),'utf8'));
 const owner=uuid(),people=Array.from({length:4},()=>uuid());
 for(const id of [owner,...people])await db.query('insert into auth.users values($1,$2)',[id,id+'@audit.invalid']);
 await db.query('insert into public.aire_creators values($1)',[owner]);
 await actor(owner);const room=await rpc('aire_create_classroom',['Auditoría de destinatarios','Fixture local']);
 const gateway=await rpc('aire_create_gateway',[room,'PC ficticia']);
 for(const id of people){await actor(owner);await rpc('aire_grant_member',[room,id+'@audit.invalid','docente'])}
 const rejected=[];let registered=0;
 for(const id of people){
  await actor(id);
  try{await rpc('aire_register_phone',[room,uuid(),'fixture-token-'+id,'Teléfono ficticio',true]);registered++}
  catch(e){rejected.push(e.message)}
 }
 assert.equal(registered,3);assert.equal(rejected.length,1);assert.match(rejected[0],/CUOTA_CELULARES/);
 await db.exec('reset role');const incident=uuid();
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,'arduino','alerta',now())",[incident,room,gateway.gateway_id]);
 await db.query("insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity) select classroom_id,$1,user_id,installation_id,'alerta' from public.aire_phones where classroom_id=$2",[incident,room]);
 const before=(await db.query("select count(*)::int n from public.aire_deliveries where status='pendiente'")).rows[0].n;
 await actor(people[0]);await rpc('aire_attention',[incident,1,'resolver','']);
 await db.exec('reset role');
 const after=(await db.query("select count(*)::int n from public.aire_deliveries where status='pendiente'")).rows[0].n;
 const cancelled=(await db.query("select count(*)::int n from public.aire_deliveries where status='cancelado'")).rows[0].n;
 assert.equal(before,3);assert.equal(after,0);assert.equal(cancelled,3);
 const report={at:new Date().toISOString(),scope:'PGlite local con las seis migraciones históricas y las dos de atención desplegadas; sin red real ni datos del usuario',authorized_test_recipients:4,registered:registered,rejected_by_phone_limit:rejected.length,deliveries_pending_before_human_attention:before,pending_after_human_attention:after,cancelled_after_human_attention:cancelled,findings:['Un cuarto destinatario autorizado no puede registrar teléfono por límite de tres por aula','Marcar atendido por una persona cancela entregas aún pendientes a los demás'],cloud_writes:0,real_push_sent:0};
 await writeFile(new URL('../../artifacts/audit-project-goals.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{await db.close()}
