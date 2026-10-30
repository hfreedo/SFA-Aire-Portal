import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';import {randomUUID as uuid} from 'node:crypto';
const db=await createCloudFixture();let checks=0;
const admin=uuid(),teacher=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
try{
 for(const id of [admin,teacher])await db.query('insert into auth.users values($1,$2)',[id,id+'@test.invalid']);
 await db.query('insert into public.aire_creators values($1)',[admin]);await actor(admin);const room=await rpc('aire_create_classroom',['USB test','School']);await rpc('aire_grant_member',[room,teacher+'@test.invalid','docente']);
 const gateway=await rpc('aire_create_gateway',[room,'USB PC']);
 await rpc('aire_register_phone_v2',[room,uuid(),uuid(),'fixture-phone-never-send-token-'+uuid(),'Android',true]);
 await actor(null,'anon');await rpc('aire_gateway_poll',[gateway.gateway_id,gateway.gateway_secret,true]);
 const run=uuid();
 await assert.rejects(()=>rpc('aire_lab_start_usb',[room,gateway.gateway_id,run,true,true]));checks++;
 await actor(teacher);await assert.rejects(()=>rpc('aire_lab_start_usb',[room,gateway.gateway_id,run,true,true]));checks++;
 await actor(admin);await assert.rejects(()=>rpc('aire_lab_start_usb',[room,gateway.gateway_id,run,true,false]));checks++;
 assert.equal(await rpc('aire_lab_start_usb',[room,gateway.gateway_id,run,true,true]),run);checks++;
 assert.equal(await rpc('aire_lab_start_usb',[room,gateway.gateway_id,run,true,true]),run);checks++;
 const lab=(await rpc('aire_lab_panel',[room])).runs[0];assert.equal(lab.input_source,'usb');assert.equal(lab.duration_s,180);checks+=2;
 await actor(null,'anon');const command=(await rpc('aire_gateway_poll',[gateway.gateway_id,gateway.gateway_secret,true])).lab;assert.equal(command.input_source,'usb');checks++;
 const incident=uuid(),now=Date.now()/1000;const packet={origin_id:uuid(),seq:1,source:'simulacion',state:'alerta',sample_at:now,lab_run_id:run,observation:{mq_raw:500,temperature:23.4,humidity:52,dht_ok:true,ratio:5/3,usb_simulation:true,usb_cloud:true,lab_run_id:run},incidents:[{id:incident,source:'simulacion',severity:'alerta',opened:now,causes:['mq135']}]};
 assert.equal((await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(packet)])).accepted_seq,1);checks++;
 await db.exec('reset role');let counts=(await db.query('select (select count(*) from public.aire_readings)::int readings,(select count(*) from public.aire_deliveries)::int deliveries,(select runs from public.aire_free_usage where day=current_date) runs')).rows[0];assert.equal(counts.readings,1);assert.equal(counts.deliveries,1);assert.equal(counts.runs,1);checks+=3;
 await actor(admin);const overview=await rpc('aire_overview');assert.ok(overview.snapshots.some(s=>s.source==='simulacion'&&s.observation.mq_raw===500));checks++;
 await rpc('aire_lab_stop',[run]);await actor(null,'anon');const later={...packet,seq:2,sample_at:now+1,incidents:[{...packet.incidents[0],id:uuid()}]};await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(later)]);
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_deliveries')).rows[0].n,1);checks++;
 console.log(JSON.stringify({checks,passed:true,note:'PGlite fixture; no real FCM.'}));
}finally{await db.close()}
