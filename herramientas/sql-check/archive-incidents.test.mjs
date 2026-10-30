import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture({through:'20261026000132_gateway_lifecycle_capabilities.sql'});let checks=0;
const owner=uuid(),coord=uuid(),teacher=uuid(),tech=uuid(),observer=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role);}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) v`,args)).rows[0].v;}
async function denied(work){await assert.rejects(work);checks++;}
async function caps(id){return (await rpc('aire_overview')).incidents.find(i=>i.id===id).capabilities;}
try {
 for(const [id,label] of [[owner,'owner'],[coord,'coord'],[teacher,'teacher'],[tech,'tech'],[observer,'observer']])await db.query('insert into auth.users values($1,$2)',[id,`${label}@test.invalid`]);
 await db.query('insert into public.aire_creators values($1)',[owner]);
 await actor(owner);const room=await rpc('aire_create_classroom',['Archivo administrativo','Prueba']);
 for(const [label,role] of [['coord','docente'],['teacher','docente'],['tech','admin'],['observer','observador']])await rpc('aire_grant_member',[room,`${label}@test.invalid`,role]);
 await rpc('aire_set_duty',[room,0,coord,teacher,null]);
 const gateway=await rpc('aire_create_gateway',[room,'PC anterior']);
 const incident=uuid(),instruction=uuid();await db.exec('reset role');
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at,coordinator_id) values($1,$2,$3,'arduino','alerta',now(),$4)",[incident,room,gateway.gateway_id,coord]);
 await db.query("insert into public.aire_snapshots values($1,'arduino',$2,now(),now(),'normal','{}')",[gateway.gateway_id,room]);
 await actor(teacher);let policy=await caps(incident);assert.ok(policy.can_attend&&!policy.can_resolve&&!policy.can_archive);checks++;
 await actor(tech);policy=await caps(incident);assert.ok(!policy.can_attend&&!policy.can_resolve&&!policy.can_archive);checks++;
 await actor(coord);policy=await caps(incident);assert.ok(policy.can_resolve&&!policy.can_archive);checks++;
 await denied(()=>rpc('aire_archive_incident',[incident,1,'No procede sin retiro ni ensayo terminal']));
 await rpc('aire_issue_instruction',[incident,1,instruction,'Ventilar aula','Contexto de prueba',30]);
 policy=await caps(incident);assert.ok(!policy.can_resolve);checks++;
 await actor(tech);await rpc('aire_revoke_gateway',[gateway.gateway_id,1,'Sustitución de PC y credencial']);
 await db.exec('reset role');let item=(await db.query('select * from public.aire_incidents where id=$1',[incident])).rows[0];
 assert.equal(item.status,'pendiente');assert.equal(item.closure_kind,null);checks++;
 for(const id of [owner,teacher,tech,observer]){await actor(id);await denied(()=>rpc('aire_archive_incident',[incident,item.revision,'No soy coordinación vigente']));}
 await actor(null,'anon');await denied(()=>rpc('aire_archive_incident',[incident,item.revision,'No autenticado']));
 await actor(coord);policy=await caps(incident);assert.ok(policy.can_archive&&!policy.can_resolve);checks++;
 await denied(()=>rpc('aire_archive_incident',[incident,item.revision-1,'Revisión anterior']));
 await denied(()=>rpc('aire_archive_incident',[incident,item.revision,null]));await denied(()=>rpc('aire_archive_incident',[incident,item.revision,'x']));
 const note='Se retiró el receptor. Se atendió al grupo por el protocolo institucional, sin verificar normalización.';
 await rpc('aire_archive_incident',[incident,item.revision,note]);
 await rpc('aire_archive_incident',[incident,item.revision,note]);
 await db.exec('reset role');const archived=(await db.query('select * from public.aire_incidents where id=$1',[incident])).rows[0];
 assert.equal(archived.status,'resuelto');assert.equal(archived.closure_kind,'administrativo');assert.equal(archived.closed_by,coord);assert.equal(archived.closure_reason,note);assert.ok(archived.closed_at);assert.match(archived.note,/ARCHIVO ADMINISTRATIVO.*No confirma normalización/);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_attention_log where incident_id=$1 and action=$2',[incident,'archivar'])).rows[0].n,1);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_coord_events where incident_id=$1 and kind=$2',[incident,'archivo_administrativo'])).rows[0].n,1);checks++;
 const retired=(await db.query('select status,action,response from public.aire_instructions where id=$1',[instruction])).rows[0];assert.equal(retired.status,'reemplazada');assert.equal(retired.action,'Ventilar aula');assert.notEqual(retired.status,'realizada');checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_snapshots where gateway_id=$1',[gateway.gateway_id])).rows[0].n,0);checks++;
 await actor(owner);await rpc('aire_set_duty',[room,1,coord,teacher,null]);checks++;
 await actor(coord);policy=await caps(incident);assert.ok(!policy.can_archive&&!policy.can_resolve&&!policy.can_attend);checks++;
 // Un ensayo cancelado/agotado también puede archivarse sin inventar normalización.
 await actor(owner);const replacement=await rpc('aire_create_gateway',[room,'PC actual']);
 for(const terminal of ['cancelado','finalizado','error','vencido']){
  const run=uuid(),sim=uuid();await db.exec('reset role');
  await db.query("insert into public.aire_lab_runs(id,classroom_id,gateway_id,created_by,expires_at,temperature,humidity,mq_raw,duration_s,status) values($1,$2,$3,$4,now()+$5::interval,25,50,500,60,$6)",[run,room,replacement.gateway_id,owner,terminal==='vencido'?'-1 minute':'1 minute',terminal==='vencido'?'ejecutando':terminal]);
  await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at,coordinator_id,lab_run_id) values($1,$2,$3,'simulacion','alerta',now(),$4,$5)",[sim,room,replacement.gateway_id,coord,run]);
  await actor(coord);assert.ok((await caps(sim)).can_archive);await rpc('aire_archive_incident',[sim,1,`Fin técnico del ensayo ${terminal}, sin normalización verificada`]);checks++;
 }
 // Ningún flujo alternativo de archivo concede ejecución directa al helper privado.
 await actor(tech);await denied(()=>db.query('select aire_private.incident_capabilities($1)',[incident]));
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from net.test_requests')).rows[0].n,0);checks++;
 await writeFile(new URL('../../artifacts/archive-incidents-sql-report.json',import.meta.url),JSON.stringify({checks,real_cloud_requests:0,real_push_sent:0,scope:'Explicit coordinator archive; retired receiver and terminal/expired lab, no fake normal readings, retained instruction/audit trace, idempotency and duty release'},null,2));
 console.log(`PASS: ${checks} comprobaciones de archivo administrativo y capacidades operativas.`);
}finally{await db.close()}
