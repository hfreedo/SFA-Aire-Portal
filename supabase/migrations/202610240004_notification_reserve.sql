-- SFA Aire 0.5. Aplicar después de 001, 002 y 003. Sin servicios adicionales.
begin;
alter table public.aire_free_usage add column operational_push_jobs integer not null default 0;
alter table public.aire_free_usage add column laboratory_push_jobs integer not null default 0;
alter table public.aire_free_usage add column operational_push_omitted integer not null default 0;
alter table public.aire_free_usage add column laboratory_push_omitted integer not null default 0;
-- Conservar el total histórico. Lo no clasificable se carga a operación.
update public.aire_free_usage u set laboratory_push_jobs=least(u.push_jobs,
 (select count(*)::integer from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where d.created_at::date=u.day and i.source='simulacion'));
update public.aire_free_usage set operational_push_jobs=push_jobs-laboratory_push_jobs;
alter table public.aire_free_usage add constraint aire_usage_split check(push_jobs=operational_push_jobs+laboratory_push_jobs and operational_push_jobs>=0 and laboratory_push_jobs>=0);
alter table public.aire_incidents add column push_omitted_operational integer not null default 0;
alter table public.aire_incidents add column push_omitted_laboratory integer not null default 0;

-- BEFORE reserva cupo por fila tras descartar duplicados. Un rollback revierte también el contador.
-- El mismo bloqueo serializa la comprobación y el incremento en todas las aulas.
create function public.aire_delivery_guard() returns trigger
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; usage public.aire_free_usage; lab_id uuid;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=new.incident_id;
 if item.id is null or new.classroom_id is distinct from item.classroom_id then raise exception 'Entrega sin incidente válido'; end if;
 if exists(select 1 from public.aire_deliveries d where d.incident_id=new.incident_id and d.user_id=new.user_id and d.installation_id=new.installation_id and (d.severity=new.severity or (new.event_id is not null and d.event_id=new.event_id))) then return null; end if;
 if item.source='simulacion' then
  lab_id:=coalesce(item.lab_run_id,nullif(current_setting('aire.ingest_lab_id',true),'')::uuid);
  if not exists(select 1 from public.aire_lab_runs r where r.id=lab_id and r.classroom_id=item.classroom_id and r.gateway_id=item.gateway_id and r.allow_push and r.status not in ('cancelado','error') and exists(select 1 from public.aire_members m where m.classroom_id=r.classroom_id and m.user_id=r.created_by and m.role='admin')) then return null; end if;
 end if;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 select * into usage from public.aire_free_usage where day=current_date for update;
 if usage.push_jobs>=100 or (item.source='simulacion' and usage.laboratory_push_jobs>=20) or (item.source='arduino' and usage.operational_push_jobs>=80) then
  update public.aire_free_usage set operational_push_omitted=operational_push_omitted+case when item.source='arduino' then 1 else 0 end,
    laboratory_push_omitted=laboratory_push_omitted+case when item.source='simulacion' then 1 else 0 end where day=current_date;
  update public.aire_incidents set push_omitted_operational=push_omitted_operational+case when item.source='arduino' then 1 else 0 end,
    push_omitted_laboratory=push_omitted_laboratory+case when item.source='simulacion' then 1 else 0 end where id=item.id;
  return null;
 end if;
 update public.aire_free_usage set push_jobs=push_jobs+1,
  operational_push_jobs=operational_push_jobs+case when item.source='arduino' then 1 else 0 end,
  laboratory_push_jobs=laboratory_push_jobs+case when item.source='simulacion' then 1 else 0 end where day=current_date;
 return new;
end $$;
create trigger aire_delivery_guard before insert on public.aire_deliveries for each row execute function public.aire_delivery_guard();
revoke all on function public.aire_delivery_guard() from public,anon,authenticated;


create or replace function public.aire_free_budget() returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('plan','free_only','readings_today',coalesce((select readings from public.aire_free_usage where day=current_date),0),
  'readings_limit',3000,'runs_today',coalesce((select runs from public.aire_free_usage where day=current_date),0),'runs_limit',12,
  'push_jobs_today',coalesce((select push_jobs from public.aire_free_usage where day=current_date),0),'push_limit',100,
  'operational_push_today',coalesce((select operational_push_jobs from public.aire_free_usage where day=current_date),0),'operational_push_limit',80,
  'laboratory_push_today',coalesce((select laboratory_push_jobs from public.aire_free_usage where day=current_date),0),'laboratory_push_limit',20,
  'operational_push_omitted_today',coalesce((select operational_push_omitted from public.aire_free_usage where day=current_date),0),
  'laboratory_push_omitted_today',coalesce((select laboratory_push_omitted from public.aire_free_usage where day=current_date),0),
  'response_bytes_month',coalesce((select sum(response_bytes) from public.aire_free_usage where day>=date_trunc('month',now())::date),0),
  'response_budget_bytes',268435456,'readings_rows',(select count(*) from public.aire_readings),'rows_limit',50000,
  'database_bytes',pg_database_size(current_database()),'database_guard_bytes',314572800,
  'normal_sample_s',60,'normal_poll_s',60,'note','Contadores de esta aplicación; Usage del proveedor es la referencia oficial')
$$;

create or replace function public.aire_ingest(p_gateway_id uuid,p_secret text,p_packet jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb; g public.aire_gateways; run public.aire_lab_runs; item jsonb;
 before_count bigint; after_count bigint;
begin
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 perform pg_advisory_xact_lock(173034001);
 select * into g from public.aire_gateways where id=p_gateway_id for update;
 -- El reintento de un paquete confirmado nunca consume cuota de nuevo.
 if (p_packet->>'seq')::bigint<=g.last_seq then return public.aire_ingest_v02(p_gateway_id,p_secret,p_packet); end if;
 if p_packet->>'source'='simulacion' then
  select * into run from public.aire_lab_runs where id=(p_packet->>'lab_run_id')::uuid and gateway_id=p_gateway_id;
  if not found then raise exception 'Simulación sin prueba administrativa autorizada'; end if;
  if (p_packet->'observation'->>'lab_run_id') is distinct from run.id::text then raise exception 'El origen de prueba debe acompañar a la medición'; end if;
  if to_timestamp((p_packet->>'sample_at')::double precision)>run.expires_at
   or to_timestamp((p_packet->>'sample_at')::double precision)<run.created_at-interval '5 seconds' then raise exception 'Prueba cancelada o medición fuera del período autorizado'; end if;
  if run.status in ('cancelado','error') or not exists(select 1 from public.aire_members where classroom_id=run.classroom_id and user_id=run.created_by and role='admin') then
   p_packet:=jsonb_set(p_packet,'{incidents}','[]'::jsonb);
  end if;
 end if;
 -- Limpieza acotada una vez al día; nunca borra incidentes sin resolver.
 if (select last_cleanup from public.aire_free_maintenance where id=true) is distinct from current_date then
  delete from public.aire_readings where sample_at<now()-interval '30 days' or(source='simulacion' and sample_at<now()-interval '7 days');
  delete from public.aire_free_usage where day<current_date-62;
  update public.aire_free_maintenance set last_cleanup=current_date where id=true;
 end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: pausa preventiva de escrituras cloud'; end if;
 before_count:=(select count(*) from public.aire_readings);
 if before_count>=50000 then raise exception 'CUOTA_FILAS: pausa preventiva; registro local continúa'; end if;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 if(select readings from public.aire_free_usage where day=current_date)>=3000 then raise exception 'CUOTA_MEDICIONES: máximo preventivo diario'; end if;
 perform set_config('aire.ingest_lab_id',coalesce(run.id::text,''),true);
 result:=public.aire_ingest_v02(p_gateway_id,p_secret,p_packet);
 after_count:=(select count(*) from public.aire_readings);
 update public.aire_free_usage set readings=readings+(after_count-before_count)::integer where day=current_date;
 for item in select value from jsonb_array_elements(p_packet->'incidents') loop
  update public.aire_incidents set lab_run_id=case when p_packet->>'source'='simulacion' then run.id else null end,
   causes=case when jsonb_typeof(item->'causes')='array' then item->'causes' else '[]'::jsonb end
   where id=(item->>'id')::uuid and gateway_id=p_gateway_id;
 end loop;
 if p_packet->>'source'='simulacion' and not run.allow_push then
  delete from public.aire_deliveries where incident_id in(select id from public.aire_incidents where lab_run_id=run.id) and status='pendiente' and attempts=0;
 end if;
 perform set_config('aire.ingest_lab_id','',true);
 return public.aire_meter_response(result||jsonb_build_object('budget',public.aire_free_budget()));
end $$;

create or replace function public.aire_coord_event(p_incident uuid,p_instruction uuid,p_kind text,p_note text,p_target uuid) returns uuid
language plpgsql security definer set search_path='' as $$
declare eid uuid; item public.aire_incidents; n integer; expected integer;
begin
 perform pg_advisory_xact_lock(173034001);
 if pg_database_size(current_database())>=314572800 or (select count(*) from public.aire_coord_events)>=20000 then raise exception 'CUOTA_COORDINACION: archivar historial antes de continuar'; end if;
 select * into item from public.aire_incidents where id=p_incident;
 insert into public.aire_coord_events(incident_id,instruction_id,actor,kind,note) values(p_incident,p_instruction,auth.uid(),p_kind,p_note) returning id into eid;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 select least(3,count(*)::integer) into expected from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=item.classroom_id and p.user_id=p_target and (item.source<>'simulacion' or p.accept_simulations);
 if p_target is not null then
  insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity,event_id)
   select item.classroom_id,item.id,p.user_id,p.installation_id,'coord:'||eid::text,eid from public.aire_phones p
   join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id
   where p.classroom_id=item.classroom_id and p.user_id=p_target and (item.source<>'simulacion' or p.accept_simulations)
   order by p.updated_at desc limit 3;
  get diagnostics n=row_count;
  update public.aire_coord_events set notification_state=case when n>0 then case when n<expected then 'parcial_por_cupo' else 'encolado' end
   when expected=0 then 'sin_telefono_habilitado'
   when item.source='simulacion' and not exists(select 1 from public.aire_lab_runs where id=item.lab_run_id and allow_push and status not in ('cancelado','error') and exists(select 1 from public.aire_members m where m.classroom_id=aire_lab_runs.classroom_id and m.user_id=aire_lab_runs.created_by and m.role='admin')) then 'simulacion_sin_push_autorizado'
   when item.source='simulacion' then 'cupo_laboratorio_agotado' else 'cupo_operativo_agotado' end where id=eid;
 end if;
 return eid;
end $$;

create or replace function public.aire_coord_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare owner boolean;
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 owner:=exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid());
 return public.aire_meter_response(jsonb_build_object('budget',public.aire_free_budget(),'user_id',auth.uid(),'can_manage',owner,'duty',(select to_jsonb(d) from public.aire_duty d where classroom_id=p_classroom_id),
 'people',coalesce((select jsonb_agg(jsonb_build_object('id',m.user_id,'label',case when owner or m.user_id=auth.uid() or exists(select 1 from public.aire_duty t where t.classroom_id=p_classroom_id and m.user_id in (t.coordinator,t.teacher,t.deputy)) then u.email else 'Cuenta '||left(m.user_id::text,8) end,'role',m.role)) from public.aire_members m join auth.users u on u.id=m.user_id where m.classroom_id=p_classroom_id),'[]'::jsonb),
 'instructions',coalesce((select jsonb_agg(to_jsonb(x)) from(select x.* from public.aire_instructions x join public.aire_incidents i on i.id=x.incident_id where i.classroom_id=p_classroom_id and i.id in (select id from public.aire_incidents where classroom_id=p_classroom_id order by opened_at desc limit 30) order by (x.status='reemplazada'),x.created_at desc limit 40)x),'[]'::jsonb),
 'events',coalesce((select jsonb_agg(to_jsonb(e)) from(select e.* from public.aire_coord_events e join public.aire_incidents i on i.id=e.incident_id where i.classroom_id=p_classroom_id order by e.created_at desc limit 60)e),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select d.id,d.incident_id,d.event_id,d.status,d.provider_id,d.received_at,d.opened_at from public.aire_deliveries d where d.classroom_id=p_classroom_id and d.event_id is not null order by d.created_at desc limit 40)d),'[]'::jsonb)));
end $$;

create or replace function public.aire_claim_push_v02(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways; result jsonb;
begin
 select * into g from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8'));
 if not found then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 update public.aire_deliveries d set status='vencido' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and d.created_at<now()-interval '5 minutes';
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and (i.status='resuelto' or not exists(select 1 from public.aire_members m where m.classroom_id=d.classroom_id and m.user_id=d.user_id));
 with jobs as (
  select d.id from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id
  where i.gateway_id=g.id and d.status in ('pendiente','reintento') and d.next_try<=now()
   and (d.lease_until is null or d.lease_until<now()) and d.attempts<5
  order by case when i.source='arduino' then 0 else 1 end,d.created_at,d.id limit 20 for update of d skip locked
 ), claimed as (
  update public.aire_deliveries d set lease_id=gen_random_uuid(),lease_until=now()+interval '60 seconds',attempts=attempts+1
  where id in (select id from jobs) returning d.*
 ) select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'lease_id',d.lease_id,'incident_id',d.incident_id,'severity',d.severity,'source',i.source,'token',p.token)),'[]'::jsonb) into result
 from claimed d join public.aire_incidents i on i.id=d.incident_id join public.aire_phones p
 on p.classroom_id=d.classroom_id and p.user_id=d.user_id and p.installation_id=d.installation_id;
 return jsonb_build_object('jobs',result);
end $$;

create or replace function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 perform pg_advisory_xact_lock(173034001);
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 -- Cancelar entregas pendientes ante reemplazo, vencimiento o revocación.
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i,public.aire_coord_events e
 where d.incident_id=i.id and i.gateway_id=p_gateway_id and d.event_id=e.id and d.status in ('pendiente','reintento')
 and (not exists(select 1 from public.aire_duty t where t.classroom_id=i.classroom_id and d.user_id in (t.coordinator,t.teacher,t.deputy))
 or (e.instruction_id is not null and exists(select 1 from public.aire_instructions x where x.id=e.instruction_id and (x.status='reemplazada' or x.expires_at<=now()))));
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i,public.aire_lab_runs r
 where d.incident_id=i.id and i.lab_run_id=r.id and i.gateway_id=p_gateway_id and d.status in ('pendiente','reintento')
 and not exists(select 1 from public.aire_members m where m.classroom_id=r.classroom_id and m.user_id=r.created_by and m.role='admin');
 result:=public.aire_claim_push_v03(p_gateway_id,p_secret);
 return jsonb_build_object('jobs',coalesce((select jsonb_agg(j.value||jsonb_build_object('severity',i.severity,'event_id',d.event_id,'event_kind',e.kind) order by case when i.source='arduino' then 0 else 1 end,d.created_at,d.id) from jsonb_array_elements(result->'jobs') j join public.aire_deliveries d on d.id=(j.value->>'id')::uuid join public.aire_incidents i on i.id=d.incident_id left join public.aire_coord_events e on e.id=d.event_id),'[]'::jsonb));
end $$;

alter function public.aire_lab_start(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean) rename to aire_lab_start_v03;
revoke all on function public.aire_lab_start_v03(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean) from public,anon,authenticated;
create function public.aire_lab_start(p_classroom_id uuid,p_gateway_id uuid,p_run_id uuid,
 p_temperature numeric,p_humidity numeric,p_mq_raw integer,p_duration_s integer,
 p_allow_push boolean default false,p_allow_takeover boolean default false,p_free_plan_confirmed boolean default false) returns uuid
language plpgsql security definer set search_path='' as $$
declare needed integer; u public.aire_free_usage;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores pueden iniciar pruebas' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(173034001);
 if p_allow_push and not exists(select 1 from public.aire_lab_runs where id=p_run_id) then
  select * into u from public.aire_free_usage where day=current_date;
  select least(3,count(*)::integer) into needed from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations;
  if coalesce(u.laboratory_push_jobs,0)+greatest(1,needed)>20 or coalesce(u.push_jobs,0)+greatest(1,needed)>100 then raise exception 'CUOTA_PUSH_LAB: sin margen para los teléfonos del ensayo; puede probar sin push'; end if;
 end if;
 return public.aire_lab_start_v03(p_classroom_id,p_gateway_id,p_run_id,p_temperature,p_humidity,p_mq_raw,p_duration_s,p_allow_push,p_allow_takeover,p_free_plan_confirmed);
end $$;
revoke all on function public.aire_lab_start(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean) from public,anon,authenticated;
grant execute on function public.aire_lab_start(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean) to authenticated;
commit;
