-- Prueba manual de notificación cloud. No evalúa persistencia ni simula una PC.
begin;
alter table public.aire_gateways add column kind text not null default 'pc' check(kind in ('pc','cloud_test'));
create unique index aire_one_cloud_test_origin on public.aire_gateways(classroom_id) where kind='cloud_test';
alter table public.aire_lab_runs add column execution_kind text not null default 'pc' check(execution_kind in ('pc','cloud_notification'));
alter table public.aire_lab_runs drop constraint aire_lab_runs_duration_s_check;
alter table public.aire_lab_runs add constraint aire_lab_runs_duration_s_check check((execution_kind='pc' and duration_s between 60 and 180) or (execution_kind='cloud_notification' and duration_s=0));

create function aire_private.notification_test_report(p_run uuid) returns jsonb
language sql stable set search_path='' as $$
 select jsonb_build_object('id',r.id,'created_at',r.created_at,'classroom_id',r.classroom_id,
 'temperature',r.temperature,'humidity',r.humidity,'mq_raw',r.mq_raw,
 'queued',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id),
 'accepted',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id and d.provider_id is not null),
 'received',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id and d.received_at is not null),
 'opened',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id and d.opened_at is not null),
 'pending',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id and d.status in ('pendiente','reintento')),
 'failed',(select count(*) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id and d.status in ('error','vencido','cancelado')),
 'deliveries',coalesce((select jsonb_agg(jsonb_build_object('status',d.status,'error',d.error,'attempts',d.attempts)) from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.lab_run_id=r.id),'[]'::jsonb))
 from public.aire_lab_runs r where r.id=p_run and r.execution_kind='cloud_notification'
$$;
revoke all on function aire_private.notification_test_report(uuid) from public,anon,authenticated,service_role;

create function public.aire_notification_test_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; eligible integer; budget jsonb;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula pueden probar notificaciones' using errcode='42501'; end if;
 update public.aire_deliveries d set status='vencido',error='DeliveryTimeout',lease_id=null,lease_until=null
 where d.classroom_id=p_classroom_id and d.status in ('pendiente','reintento') and d.created_at<now()-interval '5 minutes' and (d.lease_until is null or d.lease_until<now())
 and exists(select 1 from public.aire_incidents i join public.aire_lab_runs r on r.id=i.lab_run_id where i.id=d.incident_id and r.execution_kind='cloud_notification');
 select * into w from aire_private.push_worker where id;
 select count(*) into eligible from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations;
 budget:=public.aire_free_budget();
 return public.aire_meter_response(jsonb_build_object('cloud_ready',coalesce(w.enabled and w.firebase_secret_id is not null and w.worker_secret_id is not null and w.endpoint is not null,false),
 'cloud_error',w.last_error,'eligible_phones',eligible,'remaining',greatest(0,least(20-(budget->>'laboratory_push_today')::integer,100-(budget->>'push_jobs_today')::integer)),
 'runs_remaining',greatest(0,12-(budget->>'runs_today')::integer),
 'tests',coalesce((select jsonb_agg(aire_private.notification_test_report(r.id) order by r.created_at desc) from(select id,created_at from public.aire_lab_runs where classroom_id=p_classroom_id and execution_kind='cloud_notification' order by created_at desc limit 3)r),'[]'::jsonb)));
end $$;
revoke all on function public.aire_notification_test_panel(uuid) from public,anon,service_role;
grant execute on function public.aire_notification_test_panel(uuid) to authenticated;

create function public.aire_send_test_alert(p_classroom_id uuid,p_request_id uuid,p_profile text default 'ambos') returns jsonb
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; previous public.aire_lab_runs; eligible integer; queued integer;
 g public.aire_gateways; seq bigint; incident uuid:=gen_random_uuid(); temperature numeric; mq integer; causes jsonb; observation jsonb; usage public.aire_free_usage;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula pueden enviar pruebas' using errcode='42501'; end if;
 if p_request_id is null or p_profile is null or p_profile not in ('temperatura','mq135','ambos') then raise exception 'Prueba inválida'; end if;
 temperature:=case when p_profile='mq135' then 25 else 38 end;
 mq:=case when p_profile='temperatura' then 300 else 600 end;
 causes:=case p_profile when 'temperatura' then '["temperatura"]'::jsonb when 'mq135' then '["mq135"]'::jsonb else '["temperatura","mq135"]'::jsonb end;
 perform pg_advisory_xact_lock(173034001);
 select * into previous from public.aire_lab_runs where id=p_request_id;
 if found then
  if previous.classroom_id<>p_classroom_id or previous.created_by<>auth.uid() or previous.execution_kind<>'cloud_notification' or previous.temperature<>temperature or previous.mq_raw<>mq then raise exception 'El identificador pertenece a otra prueba' using errcode='42501'; end if;
  return public.aire_meter_response(aire_private.notification_test_report(previous.id));
 end if;
 if exists(select 1 from public.aire_lab_runs where classroom_id=p_classroom_id and created_by=auth.uid() and execution_kind='cloud_notification' and created_at>now()-interval '30 seconds') then raise exception 'Ya enviaste una prueba hace menos de 30 segundos. Revisa su resultado antes de repetir.'; end if;
 select * into w from aire_private.push_worker where id;
 if not coalesce(w.enabled and w.firebase_secret_id is not null and w.worker_secret_id is not null and w.endpoint is not null,false) then raise exception 'El emisor cloud no está configurado'; end if;
 if coalesce((select dispatches from aire_private.push_worker_usage where day=current_date),0)>=600 or coalesce((select sum(dispatches) from aire_private.push_worker_usage where day>=date_trunc('month',now())::date),0)>=10000 then raise exception 'Se alcanzó el presupuesto preventivo del emisor cloud'; end if;
 select count(*) into eligible from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations;
 if eligible=0 then raise exception 'Esta aula no tiene teléfonos habilitados para simulaciones. Activa los avisos de esta aula en Android.'; end if;
 if pg_database_size(current_database())>=314572800 or (select count(*) from public.aire_readings)>=50000 then raise exception 'Se alcanzó la guarda preventiva de almacenamiento'; end if;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 select * into usage from public.aire_free_usage where day=current_date for update;
 if usage.runs>=12 or usage.readings>=3000 then raise exception 'Se alcanzó el presupuesto preventivo de pruebas o mediciones de hoy'; end if;
 if usage.laboratory_push_jobs+eligible>20 or usage.push_jobs+eligible>100 then raise exception 'El presupuesto restante no alcanza para todos los teléfonos habilitados; no se envió la prueba'; end if;
 select * into g from public.aire_gateways where classroom_id=p_classroom_id and kind='cloud_test';
 if not found then
  insert into public.aire_gateways(classroom_id,name,secret_hash,kind) values(p_classroom_id,'Pruebas cloud',sha256(convert_to(gen_random_uuid()::text||gen_random_uuid()::text,'UTF8')),'cloud_test') returning * into g;
 elsif not g.enabled then raise exception 'Las pruebas cloud están deshabilitadas para esta aula'; end if;
 update public.aire_gateways set last_seq=last_seq+1 where id=g.id returning last_seq into seq;
 insert into public.aire_lab_runs(id,classroom_id,gateway_id,created_by,expires_at,temperature,humidity,mq_raw,duration_s,allow_push,status,message,execution_kind)
 values(p_request_id,p_classroom_id,g.id,auth.uid(),now()+interval '5 minutes',temperature,55,mq,0,true,'finalizado','Aviso manual de prueba creado en nube; no evalúa Arduino ni persistencia de sensores','cloud_notification');
 observation:=jsonb_build_object('temperature',temperature,'humidity',55,'dht_ok',true,'mq_raw',mq,'ratio',mq/300.0,'lab_run_id',p_request_id,'notification_test',true,'causes',causes);
 insert into public.aire_readings(classroom_id,gateway_id,seq,source,sample_at,state,observation) values(p_classroom_id,g.id,seq,'simulacion',now(),'alerta',observation);
 insert into public.aire_snapshots(gateway_id,source,classroom_id,sample_at,state,observation) values(g.id,'simulacion',p_classroom_id,now(),'alerta',observation)
 on conflict(gateway_id,source) do update set sample_at=excluded.sample_at,ingested_at=now(),state=excluded.state,observation=excluded.observation;
 insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at,note,lab_run_id,causes)
 values(incident,p_classroom_id,g.id,'simulacion','alerta',now(),'PRUEBA DE NOTIFICACIÓN · Datos sintéticos; no representa una medición física.',p_request_id,causes);
 insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity)
 select p_classroom_id,incident,p.user_id,p.installation_id,'alerta' from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations order by p.user_id,p.installation_id;
 get diagnostics queued=row_count;
 if queued<>eligible then raise exception 'Cambió la lista de teléfonos; actualiza y vuelve a intentar. La operación se revirtió.'; end if;
 update public.aire_free_usage set runs=runs+1,readings=readings+1 where day=current_date;
 return public.aire_meter_response(aire_private.notification_test_report(p_request_id));
end $$;
revoke all on function public.aire_send_test_alert(uuid,uuid,text) from public,anon,service_role;
grant execute on function public.aire_send_test_alert(uuid,uuid,text) to authenticated;

create or replace function aire_private.bind_notification_jobs(p_result jsonb) returns jsonb
language sql stable set search_path='' as $$
 select p_result || jsonb_build_object('jobs',coalesce((select jsonb_agg(j.value || jsonb_build_object('installation_id',d.installation_id,'notification_test',coalesce(r.execution_kind='cloud_notification',false)) order by j.ordinality)
 from jsonb_array_elements(p_result->'jobs') with ordinality j(value,ordinality)
 join public.aire_deliveries d on d.id=(j.value->>'id')::uuid
 join public.aire_incidents i on i.id=d.incident_id left join public.aire_lab_runs r on r.id=i.lab_run_id),'[]'::jsonb))
$$;
revoke all on function aire_private.bind_notification_jobs(jsonb) from public,anon,authenticated,service_role;

create or replace function public.aire_create_gateway(p_classroom_id uuid,p_name text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare secret text; gateway uuid;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 if p_name is null or length(trim(p_name)) not between 2 and 100 then raise exception 'Nombre de receptor inválido'; end if;
 perform pg_advisory_xact_lock(173034001);
 if (select count(*) from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id and enabled)>=2 then
  raise exception 'CUOTA_RECEPTORES: máximo de dos receptores activos por aula. Revoque el anterior para sustituirlo';
 end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: se alcanzó la guarda preventiva de tamaño'; end if;
 secret:=gen_random_uuid()::text||gen_random_uuid()::text;
 insert into public.aire_gateways(classroom_id,name,secret_hash)
 values(p_classroom_id,trim(p_name),sha256(convert_to(secret,'UTF8'))) returning id into gateway;
 return jsonb_build_object('gateway_id',gateway,'gateway_secret',secret,'classroom_id',p_classroom_id);
end $$;

create or replace function public.aire_admin_capabilities(p_classroom_id uuid default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare role_name text; creator boolean; owner boolean; rooms integer; active_count integer;
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 role_name:=public.aire_role(p_classroom_id);
 if p_classroom_id is not null and role_name is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 creator:=exists(select 1 from public.aire_creators where user_id=auth.uid());
 owner:=exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid());
 select count(*) into rooms from public.aire_classrooms;
 select count(*) into active_count from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id and enabled;
 return public.aire_meter_response(jsonb_build_object(
  'classroom_id',p_classroom_id,'can_create_classroom',creator and rooms<3,
  'can_manage_members',coalesce(role_name='admin',false),'can_manage_gateways',coalesce(role_name='admin',false),
  'create_reason',case when not creator then 'Esta cuenta no está habilitada para crear aulas' when rooms>=3 then 'Se alcanzó el máximo preventivo de tres aulas' else null end,
  'members_reason',case when role_name is distinct from 'admin' then 'Solo administradores del aula pueden gestionar personas' else null end,
  'gateway_limit',2,'active_gateways',active_count,
  'gateway_total',(select count(*) from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id),
  'gateways',case when role_name='admin' then coalesce((select jsonb_agg(jsonb_build_object(
    'id',id,'name',name,'enabled',enabled,'revision',revision,'last_seen_at',last_seen_at,'paired',origin_id is not null,'revoked_at',revoked_at,'revoked_by',revoked_by,'revoked_reason',revoked_reason)
    order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id) from (select * from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id limit 50) listed),'[]'::jsonb) else '[]'::jsonb end));
end $$;

-- El simulador cloud no aparece como PC ni consume los cupos físicos.
create or replace function public.aire_lab_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 result:=public.aire_lab_panel_v05(p_classroom_id);
 return jsonb_set(result,'{gateways}',coalesce((select jsonb_agg(item) from jsonb_array_elements(result->'gateways') item join public.aire_gateways g on g.id=(item->>'id')::uuid where g.kind='pc'),'[]'::jsonb))||jsonb_build_object('cloud_worker',public.aire_cloud_status(p_classroom_id));
end $$;
commit;
