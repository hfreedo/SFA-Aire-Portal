import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture();let checks=0;
const users=Array.from({length:10},()=>uuid()),bindings=[];
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
try{
 for(const id of users)await db.query('insert into auth.users values($1,$2)',[id,id+'@fixture.invalid']);
 await db.query('insert into public.aire_creators values($1)',[users[0]]);await actor(users[0]);
 const room=await rpc('aire_create_classroom',['Aula colectiva','Prueba local']);const pc=await rpc('aire_create_gateway',[room,'PC']);
 for(const id of users.slice(1))await rpc('aire_grant_member',[room,id+'@fixture.invalid','docente']);
 for(const id of users){await actor(id);for(let n=0;n<2;n++){const bound=uuid();bindings.push(bound);await rpc('aire_register_phone_v2',[room,uuid(),bound,'fake-token-never-send-'+uuid(),'Android',true])}}
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_phones')).rows[0].n,20);checks++;
 await actor(users[0]);await assert.rejects(()=>rpc('aire_register_phone_v2',[room,uuid(),uuid(),'fake-extra-never-send-'+uuid(),'Extra',false]));checks++;
 await db.exec('reset role');const incident=uuid();await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,'arduino','alerta',now())",[incident,room,pc.gateway_id]);
 await db.query("insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity) select classroom_id,$1,user_id,installation_id,'alerta' from public.aire_phones",[incident]);
 await actor(users[1]);await rpc('aire_attention',[incident,1,'resolver','']);
 await db.exec('reset role');assert.equal((await db.query("select count(*)::int n from public.aire_deliveries where status='pendiente'")).rows[0].n,20);checks++;
 // Transporte PC: los avisos ambientales siguen disponibles después de la atención.
 await actor(null,'anon');const pcJobs=(await rpc('aire_claim_push',[pc.gateway_id,pc.gateway_secret])).jobs;assert.equal(pcJobs.length,20);assert.ok(pcJobs.every(j=>bindings.includes(j.installation_id)));checks+=2;
 await db.exec('reset role');await db.query('update public.aire_deliveries set lease_until=now()-interval \'1 second\'');
 await db.query("update aire_private.push_worker set enabled=true,last_auth_ok=now(),last_error=null where id");
 await actor(null,'service_role');const cloudJobs=(await rpc('aire_cloud_claim')).jobs;assert.equal(cloudJobs.length,9);assert.ok(cloudJobs.every(j=>bindings.includes(j.installation_id)));checks+=2;
 // Revocar una cuenta retira solamente sus entregas, aunque el aviso esté atendido.
 await db.exec('reset role');await db.query('delete from public.aire_members where classroom_id=$1 and user_id=$2',[room,users[2]]);await actor(null,'service_role');await rpc('aire_cloud_claim');
 await db.exec('reset role');assert.equal((await db.query("select count(*)::int n from public.aire_deliveries where user_id=$1 and status='cancelado'",[users[2]])).rows[0].n,2);checks++;
 const usage=(await db.query('select * from public.aire_free_usage')).rows[0];assert.equal(usage.operational_push_jobs,20);assert.equal(usage.laboratory_push_jobs,0);checks+=2;
 assert.equal((await db.query('select count(*)::int n from net.test_requests')).rows[0].n,0);checks++;
 await writeFile(new URL('../../artifacts/delivery-independence.json',import.meta.url),JSON.stringify({checks,registered:20,people:10,pc_claims:20,cloud_batch:9,attention_preserves_delivery:true,real_push_sent:0,cloud_requests:0},null,2));console.log('PASS: '+checks+' comprobaciones, 10 personas / 20 registros, atención independiente, contratos PC/cloud y revocación. Sin FCM real.');
}finally{await db.close()}
