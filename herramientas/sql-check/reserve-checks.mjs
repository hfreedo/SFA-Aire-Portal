import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';

export async function reserveChecks({db,actor,rpc,denied,owner,teacher,room,gateway,packet,quotaIncident}) {
 let checks=0;
 await db.exec('reset role');
 await db.exec(await readFile(new URL('../../supabase/migrations/202610240004_notification_reserve.sql',import.meta.url),'utf8'));checks++;
 const usage=async()=>{await db.exec('reset role');return (await db.query('select * from public.aire_free_usage where day=current_date')).rows[0]};
 let u=await usage();assert.equal(u.push_jobs,u.operational_push_jobs+u.laboratory_push_jobs);checks++;
 await actor(teacher);await denied(()=>db.query('update public.aire_free_usage set laboratory_push_jobs=0'));
 await denied(()=>rpc('aire_lab_start_v03',[room,gateway.gateway_id,'01010101-0101-4101-8101-010101010101',38,55,300,90,true,false,true]));
 await db.exec('reset role');await db.exec("update public.aire_free_usage set readings=0,runs=0,push_jobs=0,operational_push_jobs=0,laboratory_push_jobs=0 where day=current_date; update public.aire_lab_runs set status='cancelado',created_at=now()-interval '31 seconds'");
 await actor(owner);await rpc('aire_register_phone',[room,'owner-phone-v05','fake-token-owner-no-send-123456','Dirección prueba',true]);
 await actor(null,'anon');await rpc('aire_gateway_poll',[gateway.gateway_id,gateway.gateway_secret,true]);
 await actor(owner);
 const run='05050505-0505-4505-8505-050505050505';
 await rpc('aire_lab_start',[room,gateway.gateway_id,run,38,55,300,90,true,false,true]);checks++;
 await db.exec('reset role');await db.exec('update public.aire_free_usage set push_jobs=19,laboratory_push_jobs=19 where day=current_date');
 const labIncident='06060606-0606-4606-8606-060606060606';
 const sim={...packet,seq:10,lab_run_id:run,sample_at:Date.now()/1000,observation:{...packet.observation,lab_run_id:run},incidents:[{id:labIncident,source:'simulacion',severity:'alerta',opened:Date.now()/1000}]};
 await actor(null,'anon');let accepted=await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(sim)]);
 assert.equal(accepted.accepted_seq,10);checks++;
 u=await usage();assert.equal(u.laboratory_push_jobs,20);assert.equal(u.operational_push_jobs,0);assert.equal(u.push_jobs,20);assert.equal(u.laboratory_push_omitted,1);checks++;
 assert.equal((await db.query('select count(*)::int n from public.aire_deliveries where incident_id=$1',[labIncident])).rows[0].n,1);checks++;
 await actor(null,'anon');await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(sim)]);
 u=await usage();assert.equal(u.laboratory_push_jobs,20);assert.equal(u.laboratory_push_omitted,1);assert.equal(u.readings,1);checks++;
 // Con el laboratorio lleno todavía se registran y notifican incidentes reales.
 const realIncident='07070707-0707-4707-8707-070707070707';
 const real={...packet,seq:11,source:'arduino',sample_at:Date.now()/1000,incidents:[{id:realIncident,source:'arduino',severity:'alerta',opened:Date.now()/1000}]};
 await actor(null,'anon');accepted=await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify(real)]);
 assert.equal(accepted.accepted_seq,11);assert.equal(accepted.budget.operational_push_today,2);checks++;
 u=await usage();assert.equal(u.operational_push_jobs,2);assert.equal(u.laboratory_push_jobs,20);assert.equal(u.push_jobs,22);checks++;
 await actor(null,'anon');const jobs=(await rpc('aire_claim_push',[gateway.gateway_id,gateway.gateway_secret])).jobs;
 assert.ok(jobs.some(j=>j.incident_id===realIncident));
 let sawLab=false;for(const job of jobs){if(job.source==='simulacion')sawLab=true;else assert.equal(sawLab,false,'La cola debe priorizar operación real')};checks++;
 // Reintentos de transporte no crean ni vuelven a contar destinatarios.
 const retry=jobs.find(j=>j.incident_id===realIncident);
 await rpc('aire_finish_push',[gateway.gateway_id,gateway.gateway_secret,retry.id,retry.lease_id,null,'TemporaryError']);
 await db.exec('reset role');await db.query("update public.aire_deliveries set next_try=now()-interval '1 second' where id=$1",[retry.id]);
 await actor(null,'anon');assert.ok((await rpc('aire_claim_push',[gateway.gateway_id,gateway.gateway_secret])).jobs.some(j=>j.id===retry.id));
 u=await usage();assert.equal(u.push_jobs,22);checks++;
 await actor(owner);assert.equal(await rpc('aire_lab_start',[room,gateway.gateway_id,run,38,55,300,90,true,false,true]),run);checks++;
 await assert.rejects(()=>rpc('aire_lab_start',[room,gateway.gateway_id,'08080808-0808-4808-8808-080808080808',38,55,300,90,true,false,true]),/CUOTA_PUSH_LAB/);checks++;
 // Indicaciones de simulación usan el cupo de laboratorio, nunca el operativo.
 await rpc('aire_take_coordination',[labIncident,1,'Suplencia en simulación']);
 await rpc('aire_issue_instruction',[labIncident,2,'09090909-0909-4909-8909-090909090909','Acción de ensayo','Prueba sin margen push',30]);
 let panel=await rpc('aire_coord_panel',[room]);
 assert.equal(panel.events.find(e=>e.instruction_id==='09090909-0909-4909-8909-090909090909').notification_state,'cupo_laboratorio_agotado');checks++;
 u=await usage();assert.equal(u.operational_push_jobs,2);assert.equal(u.push_jobs,22);checks++;
 // Si una inserción falla, PostgreSQL revierte también la reserva del trigger.
 await db.exec('reset role');
 await assert.rejects(()=>db.query("insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity) values($1,$2,'99999999-9999-4999-8999-999999999999','no-phone','invalid-user')",[room,realIncident]));
 u=await usage();assert.equal(u.push_jobs,22);checks++;
 // Un duplicado no consume cupo ni incrementa omisiones.
 const dupe=(await db.query('select * from public.aire_deliveries where id=$1',[retry.id])).rows[0];
 await db.query('insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity) values($1,$2,$3,$4,$5) on conflict do nothing',[dupe.classroom_id,dupe.incident_id,dupe.user_id,dupe.installation_id,dupe.severity]);
 u=await usage();assert.equal(u.push_jobs,22);assert.equal(u.operational_push_omitted,0);checks++;
 // Al llenar ambas reservas se omite push, sin rechazar lecturas/incidentes.
 await db.exec('update public.aire_free_usage set push_jobs=100,operational_push_jobs=80 where day=current_date');
 const fullIncident='10101010-1010-4010-8010-101010101010';
 await actor(null,'anon');accepted=await rpc('aire_ingest',[gateway.gateway_id,gateway.gateway_secret,JSON.stringify({...real,seq:12,incidents:[{id:fullIncident,source:'arduino',severity:'alerta',opened:Date.now()/1000}]})]);
 assert.equal(accepted.accepted_seq,12);assert.equal(accepted.budget.operational_push_omitted_today,2);checks++;
 u=await usage();assert.equal(u.readings,3);assert.equal(u.push_jobs,100);checks++;
 assert.equal((await db.query('select push_omitted_operational from public.aire_incidents where id=$1',[fullIncident])).rows[0].push_omitted_operational,2);checks++;
 await actor(owner);const ov=await rpc('aire_overview');const inc=ov.incidents.find(i=>i.id===quotaIncident);
 await rpc('aire_issue_instruction',[quotaIncident,inc.revision,'11112222-1111-4111-8111-111111111111','Indicación registrada','Cupo operativo agotado',30]);
 panel=await rpc('aire_coord_panel',[room]);
 assert.equal(panel.events.find(e=>e.instruction_id==='11112222-1111-4111-8111-111111111111').notification_state,'cupo_operativo_agotado');
 assert.equal(panel.budget.operational_push_limit,80);assert.equal(panel.budget.laboratory_push_limit,20);checks++;
 await rpc('aire_lab_stop',[run]);
 await db.exec('reset role');await db.query("update public.aire_lab_runs set created_at=now()-interval '31 seconds' where id=$1",[run]);
 await actor(owner);await rpc('aire_lab_start',[room,gateway.gateway_id,'12121212-1212-4212-8212-121212121212',38,55,300,90,false,false,true]);checks++;
 await actor(teacher);await denied(()=>rpc('aire_lab_start',[room,gateway.gateway_id,'13131313-1313-4313-8313-131313131313',38,55,300,90,false,false,true]));
 await denied(()=>db.query('select * from public.aire_free_usage'));
 return checks;
}
