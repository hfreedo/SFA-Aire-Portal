import {createCloudFixture} from './cloud-fixture.mjs';
import assert from 'node:assert/strict';
import {randomUUID as uuid} from 'node:crypto';
import {message} from '../../supabase/functions/aire-push/core.ts';
const db=await createCloudFixture();const admin=uuid(),outsider=uuid(),room=uuid(),gateway=uuid(),incident=uuid();let checks=0;
try{
 await db.query("insert into auth.users values($1,'admin@example.test'),($2,'other@example.test')",[admin,outsider]);
 await db.query("insert into public.aire_classrooms(id,name,owner_id) values($1,'Aula evidencia',$2)",[room,admin]);
 await db.query("insert into public.aire_members values($1,$2,'admin')",[room,admin]);
 await db.query("insert into public.aire_gateways(id,classroom_id,name,secret_hash) values($1,$2,'PC prueba',decode(repeat('aa',32),'hex'))",[gateway,room]);
 const reading=async(temp,mq)=>db.query("insert into public.aire_readings(classroom_id,gateway_id,seq,source,sample_at,state,observation) values($1,$2,$3,'arduino',now(),'alerta',$4)",[room,gateway,mq,{temperature:temp,humidity:55,mq_raw:mq,dht_ok:true,private_note:'never copy'}]);
 // Same transaction packet -> incident; only whitelisted values are captured.
 await db.exec('begin');await reading(36,600);
 await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,'arduino','aviso',now())",[incident,room,gateway]);await db.exec('commit');
 const get=async()=> (await db.query('select * from public.aire_incidents where id=$1',[incident])).rows[0];
 const initial=await get();assert.equal(initial.trigger_observation.temperature,36);assert.equal(initial.trigger_observation.mq_raw,600);assert.ok(!('private_note' in initial.trigger_observation));checks+=3;
 await reading(20,300);await db.query("update public.aire_incidents set note='atendido' where id=$1",[incident]);assert.deepEqual((await get()).trigger_observation,initial.trigger_observation);checks++;
 // Escalation can replace evidence only with a reading in that same transaction.
 await db.exec('begin');await reading(39,650);await db.query("update public.aire_incidents set severity='alerta' where id=$1",[incident]);await db.exec('commit');assert.equal((await get()).trigger_observation.temperature,39);checks++;
 const old=uuid();await db.query("insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at) values($1,$2,$3,'arduino','alerta',now()-interval '1 day')",[old,room,gateway]);assert.equal((await db.query('select trigger_observation from public.aire_incidents where id=$1',[old])).rows[0].trigger_observation,null);checks++;
 await db.query("select set_config('request.jwt.claim.sub',$1,false)",[outsider]);await db.exec('set role authenticated');const overview=(await db.query('select public.aire_overview() v')).rows[0].v;assert.ok(!overview.incidents.some(i=>i.id===incident));checks++;
 const data=message({id:uuid(),lease_id:uuid(),incident_id:incident,classroom_id:room,token:'fixture-not-send',installation_id:'binding-fixture',source:'simulacion',severity:'alerta',observation:initial.trigger_observation,classroom_name:'Aula evidencia',sample_at:initial.trigger_sample_at.toISOString()}).message.data;
 assert.equal(data.title,'Alerta simulada');assert.match(data.body,/36 °C/);assert.match(data.body,/600 ADC MQ135/);assert.ok(!data.body.includes('CO₂'));assert.ok(Object.values(data).every(x=>typeof x==='string'));checks+=5;
 const invalid=message({id:uuid(),lease_id:uuid(),incident_id:incident,classroom_id:room,token:'fixture-not-send',installation_id:'binding-fixture',source:'arduino',severity:'aviso',observation:{temperature:38,humidity:55,mq_raw:2000,dht_ok:false}}).message.data;
 assert.equal(invalid.temperature,'');assert.equal(invalid.mq_raw,'');assert.equal(invalid.title,'Aviso del aula');checks+=3;
 console.log(`PASS ${checks}: packet evidence, escalation, historical null, no snapshot substitution, RLS and descriptive payload. No real FCM.`);
}finally{await db.close()}

