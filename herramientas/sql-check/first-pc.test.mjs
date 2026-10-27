import {createCloudFixture} from './cloud-fixture.mjs';import assert from 'node:assert/strict';import {randomUUID as uuid} from 'node:crypto';
const db=await createCloudFixture(),owner=uuid(),outsider=uuid(),room=uuid(),origin=uuid(),secret='fixture-first-pc-'.padEnd(64,'x');let checks=0;
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function call(o=origin,s=secret){return(await db.query('select public.aire_enroll_pc($1,$2,$3) v',[room,o,s])).rows[0].v}
try{
 await db.query("insert into auth.users values($1,'owner@example.test'),($2,'other@example.test')",[owner,outsider]);await db.query("insert into public.aire_classrooms(id,name,owner_id) values($1,'Aula limpia',$2)",[room,owner]);await db.query("insert into public.aire_members values($1,$2,'admin')",[room,owner]);
 await actor(null,'anon');await assert.rejects(()=>call());checks++;await actor(outsider);await assert.rejects(()=>call());checks++;
 await actor(owner);const first=await call();assert.equal(first.classroom_id,room);assert.equal((await call()).gateway_id,first.gateway_id);checks++;
 await assert.rejects(()=>call(origin,'different-secret'.padEnd(64,'x')));checks++;
 await call(uuid());await assert.rejects(()=>call(uuid()));checks++;
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_gateways where classroom_id=$1',[room])).rows[0].n,2);checks++;
 console.log(`PASS ${checks}: primera PC admin, anónimo/ajeno rechazados, idempotencia, origen protegido y cuota de dos PC.`);
}finally{await db.close()}
