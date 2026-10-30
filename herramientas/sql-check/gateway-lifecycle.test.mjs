import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture();let checks=0;
const owner=uuid(),admin=uuid(),teacher=uuid(),observer=uuid(),outsider=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role);}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) v`,args)).rows[0].v;}
async function denied(work){await assert.rejects(work);checks++;}
try {
 for(const [id,label] of [[owner,'owner'],[admin,'admin'],[teacher,'teacher'],[observer,'observer'],[outsider,'outsider']])await db.query('insert into auth.users values($1,$2)',[id,`${label}@test.invalid`]);
 await db.query('insert into public.aire_creators values($1)',[owner]);
 await actor(owner);const room=await rpc('aire_create_classroom',['Receptores','Prueba']);
 for(const [label,role] of [['admin','admin'],['teacher','docente'],['observer','observador']])await rpc('aire_grant_member',[room,`${label}@test.invalid`,role]);
 let caps=await rpc('aire_admin_capabilities',[room]);assert.ok(caps.can_create_classroom&&caps.can_manage_members&&caps.can_manage_gateways);checks++;
 await actor(admin);caps=await rpc('aire_admin_capabilities',[room]);assert.ok(!caps.can_create_classroom&&caps.can_manage_members&&caps.can_manage_gateways);checks++;
 const first=await rpc('aire_create_gateway',[room,'Receptor anterior']);
 const second=await rpc('aire_create_gateway',[room,'Receptor de sustitución']);
 for(let i=2;i<10;i++)await rpc('aire_create_gateway',[room,'PC adicional '+i]);
 await denied(()=>rpc('aire_create_gateway',[room,'Undécimo receptor']));
 caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.active_gateways,10);assert.equal(caps.gateway_limit,10);checks++;
 assert.ok(!JSON.stringify(caps).includes(first.gateway_secret)&&!JSON.stringify(caps).includes('secret_hash'));checks++;
 for(const person of [teacher,observer]){
  await actor(person);caps=await rpc('aire_admin_capabilities',[room]);assert.deepEqual(caps.gateways,[]);assert.ok(!caps.can_manage_members&&!caps.can_manage_gateways);checks++;
  await denied(()=>rpc('aire_create_gateway',[room,'No permitido']));await denied(()=>rpc('aire_revoke_gateway',[first.gateway_id,1,'Retiro de prueba']));
 }
 await actor(outsider);await denied(()=>rpc('aire_admin_capabilities',[room]));await denied(()=>rpc('aire_revoke_gateway',[first.gateway_id,1,'Retiro de prueba']));
 await actor(null,'anon');await denied(()=>rpc('aire_admin_capabilities',[room]));await denied(()=>rpc('aire_revoke_gateway',[first.gateway_id,1,'Retiro de prueba']));
 await actor(admin);await denied(()=>rpc('aire_revoke_gateway',[first.gateway_id,99,'Retiro de prueba']));await denied(()=>rpc('aire_revoke_gateway',[first.gateway_id,null,'Retiro de prueba']));
 await db.exec('reset role');assert.equal((await db.query('select enabled from public.aire_gateways where id=$1',[first.gateway_id])).rows[0].enabled,true);checks++;
 // Datos ficticios separados para demostrar exactamente lo que la revocación conserva.
 const incident=uuid(),otherIncident=uuid(),run=uuid(),pending=uuid(),accepted=uuid(),otherPending=uuid();
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$3,$4,'arduino','alerta',now()),($2,$3,$5,'arduino','alerta',now())",[incident,otherIncident,room,first.gateway_id,second.gateway_id]);
 await db.query("insert into public.aire_lab_runs(id,classroom_id,gateway_id,created_by,expires_at,temperature,humidity,mq_raw,duration_s) values($1,$2,$3,$4,now()+interval '2 minutes',25,50,500,60)",[run,room,first.gateway_id,owner]);
 await db.query("insert into public.aire_snapshots values($1,'arduino',$2,now(),now(),'normal','{}'),($3,'arduino',$2,now(),now(),'normal','{}')",[first.gateway_id,room,second.gateway_id]);
 await db.query("insert into public.aire_readings(classroom_id,gateway_id,seq,source,sample_at,state,observation) values($1,$2,1,'arduino',now(),'normal','{}')",[room,first.gateway_id]);
 for(const [id,inc,bound,status] of [[pending,incident,'pending-binding','pendiente'],[accepted,incident,'accepted-binding','aceptado_fcm'],[otherPending,otherIncident,'other-binding','pendiente']])
  await db.query("insert into public.aire_deliveries(id,classroom_id,incident_id,user_id,installation_id,severity,status,lease_id,lease_until) values($1,$2,$3,$4,$5,'alerta',$6,gen_random_uuid(),now()+interval '2 minutes')",[id,room,inc,owner,bound,status]);
 await actor(admin);const revoked=await rpc('aire_revoke_gateway',[first.gateway_id,1,'Retiro de prueba']);assert.deepEqual(revoked,{id:first.gateway_id,enabled:false,revision:2});checks++;
 assert.deepEqual(await rpc('aire_revoke_gateway',[first.gateway_id,1,'Retiro de prueba']),revoked);assert.deepEqual(await rpc('aire_revoke_gateway',[first.gateway_id,2,'Retiro de prueba']),revoked);checks++;
 await db.exec('reset role');
 assert.equal((await db.query('select status from public.aire_lab_runs where id=$1',[run])).rows[0].status,'cancelado');checks++;
 assert.deepEqual((await db.query('select status,lease_id,lease_until from public.aire_deliveries where id=$1',[pending])).rows[0],{status:'cancelado',lease_id:null,lease_until:null});checks++;
 assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[accepted])).rows[0].status,'aceptado_fcm');checks++;
 assert.equal((await db.query('select status from public.aire_deliveries where id=$1',[otherPending])).rows[0].status,'pendiente');checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_readings where gateway_id=$1',[first.gateway_id])).rows[0].n,1);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_incidents where gateway_id=$1',[first.gateway_id])).rows[0].n,1);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_snapshots where gateway_id=$1',[first.gateway_id])).rows[0].n,0);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_snapshots where gateway_id=$1',[second.gateway_id])).rows[0].n,1);checks++;
 const withdrawal=(await db.query('select revoked_by,revoked_at,revoked_reason from public.aire_gateways where id=$1',[first.gateway_id])).rows[0];
 assert.equal(withdrawal.revoked_by,admin);assert.ok(withdrawal.revoked_at);assert.equal(withdrawal.revoked_reason,'Retiro de prueba');checks++;
 await actor(admin);await rpc('aire_revoke_gateway',[first.gateway_id,2,'Motivo distinto de un reintento']);
 await db.exec('reset role');assert.deepEqual((await db.query('select revoked_by,revoked_at,revoked_reason from public.aire_gateways where id=$1',[first.gateway_id])).rows[0],withdrawal);checks++;
 await actor(null,'anon');await denied(()=>rpc('aire_gateway_poll',[first.gateway_id,first.gateway_secret,false,'[]']));await denied(()=>rpc('aire_claim_push',[first.gateway_id,first.gateway_secret]));
 await actor(admin);const replacement=await rpc('aire_create_gateway',[room,'Receptor nuevo']);assert.notEqual(replacement.gateway_id,first.gateway_id);checks++;
 caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.active_gateways,10);assert.equal(caps.gateways.length,11);checks++;
 await denied(()=>rpc('aire_create_gateway',[room,'Otro más']));
 await db.exec('reset role');
 for(let index=0;index<60;index++)await db.query("insert into public.aire_gateways(classroom_id,name,secret_hash,enabled) values($1,$2,decode('00','hex'),false)",[room,`Histórico ${index}`]);
 await actor(admin);caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.gateways.length,50);assert.equal(caps.gateway_total,71);assert.equal(caps.active_gateways,10);checks++;
 assert.equal(caps.gateways.filter(g=>g.enabled).length,10);checks++;
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from net.test_requests')).rows[0].n,0);checks++;
 await writeFile(new URL('../../artifacts/gateway-lifecycle-sql-report.json',import.meta.url),JSON.stringify({checks,real_cloud_requests:0,real_push_sent:0,scope:'PostgreSQL local; capabilities, ten-enabled limit, revision, idempotency, cancellation, cache/history distinction and disabled credentials'},null,2));
 console.log(`PASS: ${checks} comprobaciones de capacidades y ciclo de vida de receptores.`);
}finally{await db.close()}
