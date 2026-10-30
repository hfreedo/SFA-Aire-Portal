import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture();let checks=0;
const admin=uuid(),teacher=uuid(),observer=uuid(),outsider=uuid(),room=uuid(),gateway=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function denied(fn){await assert.rejects(fn);checks++}
async function incident(source='arduino'){
 await db.exec('reset role');const id=uuid();
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,$4,'alerta',now())",[id,room,gateway,source]);return id;
}
try{
 for(const id of [admin,teacher,observer,outsider])await db.query('insert into auth.users values($1,$2)',[id,id+'@test.invalid']);
 await db.query("insert into public.aire_classrooms(id,name,owner_id) values($1,'Aula simple',$2)",[room,admin]);
 for(const [id,role] of [[admin,'admin'],[teacher,'docente'],[observer,'observador']])await db.query('insert into public.aire_members values($1,$2,$3)',[room,id,role]);
 await db.query("insert into public.aire_gateways(id,classroom_id,name,secret_hash) values($1,$2,'PC',decode('00','hex'))",[gateway,room]);
 const first=await incident();
 for(const user of [admin,teacher]){await actor(user);const view=await rpc('aire_overview');assert.equal(view.attention_contract,2);checks++;const caps=view.incidents.find(i=>i.id===first).capabilities;assert.equal(caps.can_resolve,true);assert.equal(caps.can_attend,true);checks++}
 for(const user of [observer,outsider]){await actor(user);await denied(()=>rpc('aire_attention',[first,1,'resolver','']))}
 await actor(null,'anon');await denied(()=>rpc('aire_attention',[first,1,'resolver','']));
 await actor(teacher);await denied(()=>rpc('aire_attention',[first,0,'resolver','']));await denied(()=>rpc('aire_attention',[first,1,null,'']));await denied(()=>rpc('aire_attention',[first,1,'resolver','x'.repeat(501)]));
 // No duty, coordinator, snapshot or prescribed communication exists.
 await rpc('aire_attention',[first,1,'resolver','']);await rpc('aire_attention',[first,1,'resolver','']);
 await db.exec('reset role');const row=(await db.query('select * from public.aire_incidents where id=$1',[first])).rows[0];
 assert.equal(row.status,'resuelto');assert.equal(row.closure_kind,'atendido');assert.equal(row.closed_by,teacher);assert.equal(row.closure_reason,'');assert.match(row.note,/No confirma normalización/);checks+=5;
 assert.equal((await db.query('select count(*)::int n from public.aire_attention_log where incident_id=$1',[first])).rows[0].n,1);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_snapshots')).rows[0].n,0);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_coord_events')).rows[0].n,0);checks++;
 const second=await incident('simulacion');
 await db.query("update public.aire_gateways set enabled=false where id=$1",[gateway]);
 await db.query("insert into public.aire_instructions(id,incident_id,version,action,reason,recipient,author,validity_minutes,expires_at,status) values($1,$2,1,'Ventilar','Consejo opcional',$3,$4,60,now()+interval '1 hour','emitida')",[uuid(),second,teacher,admin]);
 await actor(admin);await rpc('aire_attention',[second,1,'resolver','x']);
 await db.exec('reset role');assert.equal((await db.query('select status from public.aire_instructions where incident_id=$1',[second])).rows[0].status,'reemplazada');checks++;
 assert.equal((await db.query('select status from public.aire_incidents where id=$1',[second])).rows[0].status,'resuelto');checks++;
 const third=await incident();await actor(teacher);await rpc('aire_attention',[third,1,'atender',null]);await rpc('aire_attention',[third,2,'resolver',null]);checks++;
 await denied(()=>rpc('aire_attention',[first,1,'atender','sobrescribir']));
 const report={at:new Date().toISOString(),checks,result:'PASS',scope:'Local PGlite; sin nube, mensajes ni FCM real',behavior:'Atender sin coordinación, comunicación, nota o normalización obligatorias; permisos y registro conservados'};
 await writeFile(new URL('../../artifacts/simple-attention-sql-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(report);
}finally{await db.close()}
