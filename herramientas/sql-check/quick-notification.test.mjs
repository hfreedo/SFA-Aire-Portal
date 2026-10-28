import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture();let checks=0;const admin=uuid(),teacher=uuid(),observer=uuid(),outsider=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function denied(action){await assert.rejects(action);checks++}
try{
 for(const id of [admin,teacher,observer,outsider])await db.query('insert into auth.users values($1,$2)',[id,id+'@test.invalid']);
 await db.query('insert into public.aire_creators values($1)',[admin]);await actor(admin);const room=await rpc('aire_create_classroom',['Sala sin PC','Prueba local']);
 for(const [id,role] of [[teacher,'docente'],[observer,'observador']])await rpc('aire_grant_member',[room,id+'@test.invalid',role]);
 for(const id of [teacher,observer,outsider]){await actor(id);await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'ambos']));await denied(()=>rpc('aire_notification_test_panel',[room]))}
 await actor(null,'anon');await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'ambos']));
 await actor(admin);await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'invalid']));await denied(()=>rpc('aire_send_test_alert',[room,null,'ambos']));
 await db.exec('reset role');await db.query("insert into vault.decrypted_secrets values($1,'fake-worker-secret-not-real','worker')",[uuid()]);const key=(await db.query('select id from vault.decrypted_secrets')).rows[0].id;
 await db.query("update aire_private.push_worker set enabled=true,worker_secret_id=$1,firebase_secret_id=gen_random_uuid(),endpoint='https://example.supabase.co/functions/v1/aire-push',last_auth_ok=now() where id",[key]);
 await actor(admin);await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'ambos']));
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_gateways')).rows[0].n,0);checks++;
 for(const user of [admin,teacher]){await actor(user);await rpc('aire_register_phone_v2',[room,uuid(),uuid(),'fake-token-never-send-'+uuid(),'Android',true])}
 await actor(observer);await rpc('aire_register_phone_v2',[room,uuid(),uuid(),'fake-observer-never-send-'+uuid(),'Observer',false]);
 await actor(admin);const ready=await rpc('aire_notification_test_panel',[room]);assert.equal(ready.eligible_phones,2);assert.equal(ready.cloud_ready,true);checks+=2;
 const request=uuid();const report=await rpc('aire_send_test_alert',[room,request,'ambos']);assert.equal(report.queued,2);assert.equal(report.received,0);assert.equal(report.accepted,0);checks+=3;
 assert.deepEqual(await rpc('aire_send_test_alert',[room,request,'ambos']),report);checks++;
 await denied(()=>rpc('aire_send_test_alert',[room,request,'temperatura']));await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'ambos']));
 await db.exec('reset role');const usage=(await db.query('select * from public.aire_free_usage')).rows[0];assert.equal(usage.runs,1);assert.equal(usage.readings,1);assert.equal(usage.laboratory_push_jobs,2);assert.equal(usage.operational_push_jobs,0);checks+=4;
 const origin=(await db.query('select * from public.aire_gateways')).rows[0];assert.equal(origin.kind,'cloud_test');assert.equal(origin.origin_id,null);assert.equal(origin.last_seen_at,null);checks+=3;
 assert.equal((await db.query('select duration_s from public.aire_lab_runs')).rows[0].duration_s,0);checks++;
 await actor(admin);let caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.active_gateways,0);assert.equal(caps.gateways.length,0);checks+=2;
 await rpc('aire_create_gateway',[room,'PC física 1']);await rpc('aire_create_gateway',[room,'PC física 2']);await denied(()=>rpc('aire_create_gateway',[room,'PC física 3']));
 assert.equal((await rpc('aire_lab_panel',[room])).gateways.length,2);checks++;
 await actor(null,'service_role');const jobs=(await rpc('aire_cloud_claim')).jobs;assert.equal(jobs.length,2);assert.ok(jobs.every(j=>j.notification_test===true&&j.installation_id));checks+=2;assert.ok(jobs.every(j=>j.observation.temperature===38&&j.observation.mq_raw===600&&j.sample_at&&j.classroom_name==='Sala sin PC'));checks++;
 await db.exec('reset role');await db.query("update public.aire_lab_runs set created_at=now()-interval '1 minute'");await db.query('update public.aire_free_usage set laboratory_push_jobs=19,push_jobs=19');
 await actor(admin);await denied(()=>rpc('aire_send_test_alert',[room,uuid(),'mq135']));
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_lab_runs')).rows[0].n,1);checks++;
 await db.query('update public.aire_free_usage set laboratory_push_jobs=2,push_jobs=2');await db.query("update public.aire_members set role='observador' where user_id=$1",[admin]);
 await actor(admin);await denied(()=>rpc('aire_send_test_alert',[room,request,'ambos']));
 await db.exec('reset role');await db.query("update public.aire_members set role='admin' where user_id=$1",[admin]);
 await db.query("update public.aire_deliveries set created_at=now()-interval '6 minutes',lease_until=now()-interval '1 second',status='pendiente'");
 await actor(admin);const expired=await rpc('aire_notification_test_panel',[room]);assert.equal(expired.tests[0].failed,2);assert.equal(expired.tests[0].pending,0);checks+=2;
 console.log('PASS: '+checks+' comprobaciones; prueba cloud sin PC, permisos, 2 destinatarios, idempotencia, cuotas y origen aislado. Sin FCM real.');
 await writeFile(new URL('../../artifacts/quick-notification-sql.json',import.meta.url),JSON.stringify({checks,pc_required:false,recipients:2,duplicate_deliveries:0,real_fcm_sent:false},null,2));
}finally{await db.close()}
