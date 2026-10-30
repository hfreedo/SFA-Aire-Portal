import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
const db=await createCloudFixture();let checks=0;
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args){return (await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function denied(fn){await assert.rejects(fn);checks++}
try{
 const admin=uuid(),teacher=uuid(),otherAdmin=uuid(),origin=uuid(),newSecret='test-only-new-secret-'.repeat(3);
 for(const id of [admin,teacher,otherAdmin])await db.query('insert into auth.users values($1,$2)',[id,id+'@test.invalid']);
 await db.query('insert into public.aire_creators values($1),($2)',[admin,otherAdmin]);
 await actor(admin);const oldRoom=await rpc('aire_create_classroom',['Aula anterior','Test']),room=await rpc('aire_create_classroom',['Sala 3ro. BTI','Test']);
 const old=await rpc('aire_create_gateway',[oldRoom,'PC anterior']),unused=await rpc('aire_create_gateway',[room,'PC del aula']);
 await rpc('aire_create_gateway',[room,'Móvil nombrado como PC']);
 await rpc('aire_grant_member',[room,teacher+'@test.invalid','docente']);await rpc('aire_grant_member',[room,otherAdmin+'@test.invalid','admin']);
 const args=[room,origin,newSecret,old.gateway_id,old.gateway_secret];
 for(const id of [teacher,otherAdmin]){await actor(id);await denied(()=>rpc('aire_assign_pc',args))}
 await actor(null,'anon');await denied(()=>rpc('aire_assign_pc',args));await actor(admin);
 await denied(()=>rpc('aire_assign_pc',[room,origin,'short',old.gateway_id,old.gateway_secret]));
 await denied(()=>rpc('aire_assign_pc',[room,origin,newSecret,old.gateway_id,'wrong']));
 await db.exec('reset role');await db.query('update public.aire_gateways set last_seen_at=now() where id=$1',[unused.gateway_id]);await actor(admin);const adoptedOther=await rpc('aire_assign_pc',args);assert.notEqual(adoptedOther.gateway_id,unused.gateway_id);checks++;
 await db.exec('reset role');await db.query('update public.aire_gateways set last_seen_at=null where id=$1',[unused.gateway_id]);await actor(admin);
 const freshArgs=[room,uuid(),'fresh-secret-'.repeat(5),old.gateway_id,old.gateway_secret];const result=await rpc('aire_assign_pc',freshArgs);assert.equal(result.gateway_id,unused.gateway_id);checks++;assert.equal(result.classroom_id,room);checks++;assert.equal('gateway_secret' in result,false);checks++;
 const retry=await rpc('aire_assign_pc',freshArgs);assert.deepEqual(result,retry);checks++;
 await db.exec('reset role');const previous=(await db.query('select classroom_id,enabled,secret_hash from public.aire_gateways where id=$1',[old.gateway_id])).rows[0];assert.equal(previous.classroom_id,oldRoom);assert.equal(previous.enabled,true);checks+=2;
 assert.equal((await db.query("select count(*)::int n from public.aire_gateways where classroom_id=$1 and kind='pc'",[room])).rows[0].n,2);checks++;
 await actor(admin);for(let i=2;i<10;i++)await rpc('aire_assign_pc',[room,uuid(),'extra-secret-'.repeat(5),old.gateway_id,old.gateway_secret]);
 await denied(()=>rpc('aire_assign_pc',[room,uuid(),'eleventh-secret-'.repeat(5),old.gateway_id,old.gateway_secret]));
 // Revoking the previous credential also prevents silently reusing a cached assignment.
 await db.exec('reset role');await db.query('update public.aire_gateways set enabled=false where id=$1',[old.gateway_id]);await actor(admin);await denied(()=>rpc('aire_assign_pc',args));
 console.log('PASS automatic PC assignment: '+checks+' checks; role, old scope, unused slot, retry, quota, preservation. No hardware/FCM.');
}finally{await db.close()}
