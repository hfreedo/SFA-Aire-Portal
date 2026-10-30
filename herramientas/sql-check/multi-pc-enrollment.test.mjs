import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
const db=await createCloudFixture();let checks=0;
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args){return (await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function denied(fn){await assert.rejects(fn);checks++}
try{
 const admin=uuid(),teacher=uuid(),other=uuid();
 for(const id of [admin,teacher,other])await db.query('insert into auth.users values($1,$2)',[id,id+'@test.invalid']);
 await db.query('insert into public.aire_creators values($1)',[admin]);
 await actor(admin);const a=await rpc('aire_create_classroom',['Aula A','Ensayo local']),b=await rpc('aire_create_classroom',['Aula B','Ensayo local']);
 await rpc('aire_grant_member',[a,teacher+'@test.invalid','docente']);
 const pcs=Array.from({length:4},()=>({origin:uuid(),secret:'test-only-'+uuid()+uuid()}));
 for(const pc of pcs){
  pc.a=await rpc('aire_enroll_pc',[a,pc.origin,pc.secret]);
  assert.deepEqual(await rpc('aire_enroll_pc',[a,pc.origin,pc.secret]),pc.a);checks++;
 }
 let caps=await rpc('aire_admin_capabilities',[a]);assert.equal(caps.active_gateways,4);assert.equal(caps.gateway_limit,10);checks++;
 assert.equal(new Set(pcs.map(p=>p.a.gateway_id)).size,4);checks++;
 assert.ok(!JSON.stringify(caps).includes(pcs[0].secret));checks++;
 // Each PC can visit another room and return, preserving both registrations.
 for(const pc of pcs){
  const secret='room-b-'+uuid()+uuid();
  pc.b=await rpc('aire_assign_pc',[b,pc.origin,secret,pc.a.gateway_id,pc.secret]);
  assert.deepEqual(await rpc('aire_assign_pc',[b,pc.origin,secret,pc.a.gateway_id,pc.secret]),pc.b);checks++;
  const back=await rpc('aire_assign_pc',[a,pc.origin,pc.secret,pc.b.gateway_id,secret]);
  assert.equal(back.gateway_id,pc.a.gateway_id);checks++;
  assert.equal((await rpc('aire_enroll_pc',[a,pc.origin,pc.secret])).gateway_id,pc.a.gateway_id);checks++;
 }
 for(const room of [a,b]){caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.active_gateways,4);checks++}
 await denied(()=>rpc('aire_enroll_pc',[a,pcs[0].origin,'different-secret-'.repeat(4)]));
 for(const id of [teacher,other,null]){
  await actor(id,id?'authenticated':'anon');
  await denied(()=>rpc('aire_enroll_pc',[a,uuid(),'unauthorized-'.repeat(5)]));
  await denied(()=>rpc('aire_create_gateway',[a,'No autorizado']));
 }
 await actor(admin);
 const old=pcs[0];await rpc('aire_revoke_gateway',[old.a.gateway_id,1,'Equipo retirado']);
 const freshSecret='renewed-test-'+uuid()+uuid();
 const renewed=await rpc('aire_enroll_pc',[a,old.origin,freshSecret]);
 assert.notEqual(renewed.gateway_id,old.a.gateway_id);checks++;
 assert.deepEqual(await rpc('aire_enroll_pc',[a,old.origin,freshSecret]),renewed);checks++;
 await denied(()=>rpc('aire_gateway_poll',[old.a.gateway_id,old.secret,false,'[]']));
 for(let i=4;i<10;i++)await rpc('aire_enroll_pc',[a,uuid(),'extra-test-'+uuid()+uuid()]);
 await denied(()=>rpc('aire_enroll_pc',[a,uuid(),'eleventh-test-'+uuid()+uuid()]));
 await denied(()=>rpc('aire_create_gateway',[a,'Undécima PC']));
 await denied(()=>rpc('aire_assign_pc',[a,uuid(),'over-limit-'+uuid()+uuid(),pcs[1].b.gateway_id,'invalid-previous-secret']));
 assert.deepEqual(await rpc('aire_enroll_pc',[a,old.origin,freshSecret]),renewed);checks++;
 caps=await rpc('aire_admin_capabilities',[a]);assert.equal(caps.active_gateways,10);checks++;
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from net.test_requests')).rows[0].n,0);checks++;
 const report={checks,pcs_tested:4,rooms_tested:2,retry_without_duplicates:true,revoked_credential_stays_disabled:true,real_cloud_registrations:0,real_push_sent:0,physical_other_pcs_tested:false};
 await writeFile(new URL('../../artifacts/multi-pc-enrollment-report.json',import.meta.url),JSON.stringify(report,null,2));
 console.log('PASS multi-PC enrollment: '+checks+' checks; four independent PCs, two rooms, idempotency, roles and revocation.');
}finally{await db.close()}
