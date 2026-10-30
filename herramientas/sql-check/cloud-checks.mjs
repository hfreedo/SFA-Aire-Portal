import {PGlite} from '@electric-sql/pglite';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

// Vault simulado solo para probar permisos y SQL. Nunca prueba cifrado alojado.
export async function cloudChecks() {
 const db=new PGlite(); let n=0;
 await db.exec(`create role anon; create role authenticated; create role service_role;
 create schema auth; create table auth.users(id uuid primary key,email text);
 create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 grant usage on schema auth to anon,authenticated;
 create schema vault; create table vault.decrypted_secrets(id uuid primary key,decrypted_secret text,name text);
 create function vault.create_secret(secret text,label text) returns uuid language plpgsql as $$declare i uuid:=gen_random_uuid();begin insert into vault.decrypted_secrets values(i,secret,label);return i;end$$;
 create function vault.update_secret(i uuid,secret text) returns void language sql as $$update vault.decrypted_secrets set decrypted_secret=secret where id=i$$;
 `);
 for(const file of ['202610240001_aire_cloud.sql','202610240002_admin_lab_free.sql','202610240003_coordination.sql','202610240004_notification_reserve.sql','20261025021517_cloud_push_worker.sql','20261025195629_bind_push_to_session.sql','20261025200720_harden_phone_lifecycle.sql'])
  await db.exec(await readFile(new URL('../../supabase/migrations/'+file,import.meta.url),'utf8'));
 const admin='11111111-1111-4111-8111-111111111111', teacher='22222222-2222-4222-8222-222222222222';
 await db.query('insert into auth.users values($1,$2),($3,$4)',[admin,'admin@test.invalid',teacher,'teacher@test.invalid']);
 await db.query('insert into public.aire_creators(user_id) values($1)',[admin]);
 async function actor(id,role='authenticated') {await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role);}
 async function rpc(name,args=[]) {return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) v`,args)).rows[0].v;}
 async function denied(f) {await assert.rejects(f);n++;}
 await actor(admin);const room=await rpc('aire_create_classroom',['Cloud Aula','Prueba']);
 await rpc('aire_grant_member',[room,'teacher@test.invalid','docente']);
 const gateway=await rpc('aire_create_gateway',[room,'PC']);
 await rpc('aire_register_phone',[room,'cloud-test-phone','fake-token-cloud-never-send-123456','Prueba',true]);
 await actor(null,'anon');await denied(()=>rpc('aire_cloud_claim'));
 await denied(()=>rpc('aire_cloud_open',['x'.repeat(64)]));
 await denied(()=>rpc('aire_cloud_finish',[admin,admin,'fake',null]));
 await actor(teacher);await denied(()=>rpc('aire_cloud_status',[room]));
 await denied(()=>db.query('select * from aire_private.push_worker'));
 await actor(admin);await denied(()=>rpc('aire_cloud_configure',['{}','https://wrong',true]));
 await db.exec('reset role');
 const account={type:'service_account',project_id:'sfa-aire-aulas',client_email:'sender@sfa-aire-aulas.iam.gserviceaccount.com',private_key:'-----BEGIN PRIVATE KEY-----TEST_NOT_A_KEY'};
 await denied(()=>rpc('aire_cloud_configure',[JSON.stringify({...account,project_id:'other'}),'https://taynrhyoxmweqnxlnqfj.supabase.co/functions/v1/aire-push',true]));
 await denied(()=>rpc('aire_cloud_configure',[JSON.stringify(account),'https://taynrhyoxmweqnxlnqfj.supabase.co/functions/v1/aire-push',false]));
 await rpc('aire_cloud_configure',[JSON.stringify(account),'https://taynrhyoxmweqnxlnqfj.supabase.co/functions/v1/aire-push',true]);n++;
 assert.equal((await rpc('aire_cloud_open',['bad'])).authorized,false);n++;
 const token=(await db.query("select decrypted_secret from vault.decrypted_secrets where name='aire_push_worker_token'")).rows[0].decrypted_secret;
 assert.equal((await rpc('aire_cloud_open',[token])).account.project_id,'sfa-aire-aulas');n++;
 await rpc('aire_cloud_health',[null]);
 await actor(null,'anon');
 const status=await rpc('aire_gateway_poll',[gateway.gateway_id,gateway.gateway_secret,false,'[]']);
 assert.equal(status.push_transport,'cloud');assert.equal(status.push_worker.error,null);n++;
 assert.equal((await rpc('aire_claim_push',[gateway.gateway_id,gateway.gateway_secret])).jobs.length,0);n++;
 await denied(()=>rpc('aire_claim_push',[gateway.gateway_id,'wrong']));
 const incident='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
 const packet={origin_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',seq:1,source:'arduino',state:'alerta',sample_at:Date.now()/1000,
 observation:{mq_raw:500,temperature:25,humidity:50},incidents:[{id:incident,source:'arduino',severity:'alerta',opened:Date.now()/1000}]};
 await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(packet)]);
 await db.exec('reset role');
 let jobs=(await rpc('aire_cloud_claim')).jobs;assert.equal(jobs.length,1);n++;
 assert.equal((await rpc('aire_cloud_claim')).jobs.length,0);n++;
 const job=jobs[0];assert.equal(job.installation_id,'cloud-test-phone');n++;
 await actor(teacher);await denied(()=>rpc('aire_receipt',[job.id,'cloud-test-phone','abierto']));
 await actor(admin);await denied(()=>rpc('aire_receipt',[job.id,'new-session-binding','abierto']));
 await actor(null,'service_role');await denied(()=>rpc('aire_cloud_claim_v06'));await denied(()=>rpc('aire_claim_push_v06',[gateway.gateway_id,gateway.gateway_secret]));
 await db.exec('reset role');assert.equal(job.classroom_id,room);assert.equal(job.source,'arduino');n++;
 await denied(()=>rpc('aire_cloud_finish',[job.id,admin,'fake',null]));
 await rpc('aire_cloud_finish',[job.id,job.lease_id,null,'FirebaseNetworkError']);
 assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[job.id])).rows[0].status,'reintento');n++;
 await db.exec("update public.aire_deliveries set next_try=now()-interval '1 second'");
 jobs=(await rpc('aire_cloud_claim')).jobs;assert.equal(jobs.length,1);assert.notEqual(jobs[0].lease_id,job.lease_id);n++;
 await actor(admin);await rpc('aire_receipt',[job.id,'cloud-test-phone','recibido']);
 await db.exec('reset role');await rpc('aire_cloud_finish',[job.id,jobs[0].lease_id,'fcm/mock',null]);
 assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[job.id])).rows[0].status,'recibido_app');n++;
 // Nuevas entregas, retiro del teléfono y vencimiento sin PC.
 const next={...packet,seq:2,incidents:[{...packet.incidents[0],id:'cccccccc-cccc-4ccc-8ccc-cccccccccccc'}]};
 await actor(null,'anon');await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(next)]);
 await actor(admin);await rpc('aire_unregister_phone',['cloud-test-phone']);
 await db.exec('reset role');assert.equal((await rpc('aire_cloud_claim')).jobs.length,0);n++;
 assert.equal((await db.query("select status from public.aire_deliveries where incident_id=$1",[next.incidents[0].id])).rows[0].status,'cancelado');n++;
 await db.exec('update aire_private.push_worker_usage set invocations=600 where day=current_date');
 assert.equal((await rpc('aire_cloud_open',[token])).state,'preventive_limit');n++;
 await actor(admin);const panel=await rpc('aire_cloud_status',[room]);
 assert.equal(panel.transport,'cloud');assert.equal(panel.invocations_today,600);n++;
 assert.ok(!JSON.stringify(panel).includes(token));assert.ok(!JSON.stringify(panel).includes('PRIVATE KEY'));n++;
 await db.exec('reset role');await rpc('aire_cloud_health',['FirebaseOAuthError']);
 assert.equal((await rpc('aire_cloud_claim')).jobs.length,0);n++;
 await actor(null,'anon');const bad=await rpc('aire_gateway_poll',[gateway.gateway_id,gateway.gateway_secret,false,'[]']);
 assert.equal(bad.push_worker.error,'FirebaseOAuthError');n++;
 await db.exec('reset role');
 await db.exec(`create schema net; create schema cron;
 create table net.test_requests(id bigint generated always as identity,url text,headers jsonb,body jsonb);
 create function net.http_post(url text,headers jsonb,body jsonb,timeout_milliseconds integer) returns bigint language plpgsql as $$declare i bigint;begin insert into net.test_requests(url,headers,body) values(url,headers,body) returning id into i;return i;end$$;
 create function cron.schedule(label text,expression text,command text) returns bigint language sql as $$select 1::bigint$$;`);
 const scheduler=await readFile(new URL('../../supabase/migrations/20261025021637_cloud_push_scheduler.sql',import.meta.url),'utf8');
 await db.exec(scheduler.replace(/^create extension[^;]+;/gm,''));
 await rpc('aire_cloud_health',[null]);
 await db.exec('update aire_private.push_worker_usage set invocations=0,dispatches=0');
 // Sin pendientes, no consume invocaciones. La PC no participa en este recorrido.
 assert.equal((await db.query('select aire_private.dispatch_push() v')).rows[0].v,null);n++;
 assert.ok((await db.query('select aire_private.dispatch_push(true) v')).rows[0].v);n++;
 assert.equal((await db.query('select aire_private.dispatch_push(true) v')).rows[0].v,null);n++;
 const wake=(await db.query('select headers from net.test_requests')).rows[0].headers;
 assert.equal(wake['x-sfa-worker'],token);n++;
 await db.exec("update aire_private.push_worker set last_dispatch=now()-interval '20 seconds'");
 await actor(admin);await rpc('aire_register_phone',[room,'cloud-test-phone','fake-token-cloud-never-send-123456','Prueba',true]);
 await actor(null,'anon');await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify({...packet,seq:3,incidents:[{...packet.incidents[0],id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd'}]})]);
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from net.test_requests')).rows[0].n,2);n++;
 await db.exec("update aire_private.push_worker set last_dispatch=now()-interval '20 seconds'; update aire_private.push_worker_usage set dispatches=600");
 assert.equal((await db.query('select aire_private.dispatch_push() v')).rows[0].v,null);n++;
 await db.exec('update aire_private.push_worker_usage set dispatches=0');
 await rpc('aire_cloud_health',['FirebaseOAuthError']);
 assert.equal((await db.query('select aire_private.dispatch_push(true) v')).rows[0].v,null);n++;
 await db.exec('reset role;update aire_private.push_worker set enabled=false');
 await actor(null,'anon');
 await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify({...packet,seq:4,incidents:[{...packet.incidents[0],id:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'}]})]);
 const pcJobs=(await rpc('aire_claim_push',[gateway.gateway_id,gateway.gateway_secret])).jobs;
 assert.ok(pcJobs.length>0);assert.ok(pcJobs.every(j=>j.installation_id==='cloud-test-phone'));n++;
 await denied(()=>rpc('aire_claim_push_v06',[gateway.gateway_id,gateway.gateway_secret]));
 await db.close();return n;
}
console.log(`PASS cloud: ${await cloudChecks()} comprobaciones SQL de permisos, exclusión PC, lease, acuse, revocación y guardas. FCM simulado.`);
