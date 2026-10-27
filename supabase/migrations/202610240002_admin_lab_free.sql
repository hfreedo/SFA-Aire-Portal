-- SFA Aire 0.3. Aplicar DESPUÉS de 001. Guardas propias, no son medidores de facturación.
begin;
alter table public.aire_gateways add column last_seen_at timestamptz;
alter table public.aire_gateways add column push_configured boolean not null default false;
alter table public.aire_incidents add column causes jsonb not null default '[]';
alter table public.aire_incidents add column lab_run_id uuid;
create table public.aire_lab_runs (
 id uuid primary key, classroom_id uuid not null references public.aire_classrooms,
 gateway_id uuid not null references public.aire_gateways, created_by uuid not null references auth.users,
 created_at timestamptz not null default now(), expires_at timestamptz not null,
 temperature numeric not null check(temperature between -20 and 60), humidity numeric not null check(humidity between 0 and 100),
 mq_raw integer not null check(mq_raw between 1 and 1022), duration_s integer not null check(duration_s between 60 and 180),
 allow_push boolean not null default false, allow_takeover boolean not null default false,
 status text not null default 'pendiente' check(status in ('pendiente','ejecutando','finalizado','cancelado','error')),
 message text not null default '', updated_at timestamptz not null default now());
create table public.aire_free_usage (
 day date primary key default current_date, readings integer not null default 0,
 runs integer not null default 0, push_jobs integer not null default 0, response_bytes bigint not null default 0);
create table public.aire_free_maintenance (id boolean primary key default true check(id),last_cleanup date);
insert into public.aire_free_maintenance values(true,null);
alter table public.aire_lab_runs enable row level security;
alter table public.aire_free_usage enable row level security;
alter table public.aire_free_maintenance enable row level security;
revoke all on public.aire_lab_runs,public.aire_free_usage,public.aire_free_maintenance from public,anon,authenticated;
-- Sin SELECT directo al laboratorio. Sus RPC comprueban admin incluso para leer.

create function public.aire_free_budget() returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_build_object('plan','free_only','readings_today',coalesce((select readings from public.aire_free_usage where day=current_date),0),
  'readings_limit',3000,'runs_today',coalesce((select runs from public.aire_free_usage where day=current_date),0),'runs_limit',12,
  'push_jobs_today',coalesce((select push_jobs from public.aire_free_usage where day=current_date),0),'push_limit',100,
  'response_bytes_month',coalesce((select sum(response_bytes) from public.aire_free_usage where day>=date_trunc('month',now())::date),0),
  'response_budget_bytes',268435456,'readings_rows',(select count(*) from public.aire_readings),'rows_limit',50000,
  'database_bytes',pg_database_size(current_database()),'database_guard_bytes',314572800,
  'normal_sample_s',60,'normal_poll_s',60,'note','Contadores de esta aplicación; Usage del proveedor es la referencia oficial')
$$;
revoke all on function public.aire_free_budget() from public,anon,authenticated;

create function public.aire_meter_response(p_payload jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare bytes bigint;
begin
 perform pg_advisory_xact_lock(173034001);
 bytes:=octet_length(p_payload::text);
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 if coalesce((select sum(response_bytes) from public.aire_free_usage where day>=date_trunc('month',now())::date),0)+bytes>268435456 then
  raise exception 'CUOTA_RESPUESTA: presupuesto preventivo mensual; consulte Usage y use el modo local';
 end if;
 update public.aire_free_usage set response_bytes=response_bytes+bytes where day=current_date;
 return p_payload;
end $$;
revoke all on function public.aire_meter_response(jsonb) from public,anon,authenticated;

alter function public.aire_create_classroom(text,text) rename to aire_create_classroom_v02;
revoke all on function public.aire_create_classroom_v02(text,text) from public,anon,authenticated;
create function public.aire_create_classroom(p_name text,p_school text default '') returns uuid
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(173034001);
 if (select count(*) from public.aire_classrooms)>=3 then raise exception 'CUOTA_AULAS: máximo preventivo de tres aulas'; end if;
 return public.aire_create_classroom_v02(p_name,p_school);
end $$;

create function public.aire_lab_start(p_classroom_id uuid,p_gateway_id uuid,p_run_id uuid,
 p_temperature numeric,p_humidity numeric,p_mq_raw integer,p_duration_s integer,
 p_allow_push boolean default false,p_allow_takeover boolean default false,p_free_plan_confirmed boolean default false) returns uuid
language plpgsql security definer set search_path='' as $$
declare previous public.aire_lab_runs;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores pueden iniciar pruebas' using errcode='42501'; end if;
 if p_free_plan_confirmed is distinct from true then raise exception 'Confirme que usa Supabase Free y Firebase Spark sin facturación vinculada'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into previous from public.aire_lab_runs where id=p_run_id;
 if found then
  if previous.created_by!=auth.uid() or previous.classroom_id!=p_classroom_id or previous.gateway_id!=p_gateway_id
    or previous.temperature is distinct from p_temperature or previous.humidity is distinct from p_humidity
    or previous.mq_raw is distinct from p_mq_raw or previous.duration_s is distinct from p_duration_s
    or previous.allow_push is distinct from p_allow_push or previous.allow_takeover is distinct from p_allow_takeover then raise exception 'ID de prueba ya utilizado con otro plan'; end if;
  return previous.id;
 end if;
 if not exists(select 1 from public.aire_gateways where id=p_gateway_id and classroom_id=p_classroom_id and enabled and last_seen_at>now()-interval '90 seconds') then raise exception 'Conecte un receptor PC reciente antes de iniciar'; end if;
 update public.aire_lab_runs set status='error',updated_at=now(),message='Receptor sin confirmación dentro del plazo' where gateway_id=p_gateway_id and expires_at<=now() and status in ('pendiente','ejecutando');
 if exists(select 1 from public.aire_lab_runs where gateway_id=p_gateway_id and status in ('pendiente','ejecutando')) then raise exception 'Ya existe una prueba activa'; end if;
 if exists(select 1 from public.aire_lab_runs where classroom_id=p_classroom_id and created_at>now()-interval '30 seconds') then raise exception 'Espere 30 segundos entre pruebas'; end if;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 if (select runs from public.aire_free_usage where day=current_date)>=12 then raise exception 'CUOTA_PRUEBAS: máximo de doce pruebas por día en este proyecto'; end if;
 if (select readings from public.aire_free_usage where day=current_date)+ceil(p_duration_s::numeric/3)+1>3000 then raise exception 'CUOTA_RESERVA: no queda margen de mediciones para completar la prueba'; end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: se alcanzó la guarda preventiva de tamaño'; end if;
 if p_allow_push and not exists(select 1 from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations) then raise exception 'No hay celulares habilitados para push de simulación'; end if;
 if p_allow_push and not exists(select 1 from public.aire_gateways where id=p_gateway_id and push_configured) then raise exception 'El receptor no detectó credencial FCM; revise Firebase'; end if;
 insert into public.aire_lab_runs(id,classroom_id,gateway_id,created_by,expires_at,temperature,humidity,mq_raw,duration_s,allow_push,allow_takeover)
 values(p_run_id,p_classroom_id,p_gateway_id,auth.uid(),now()+make_interval(secs=>p_duration_s+45),p_temperature,p_humidity,p_mq_raw,p_duration_s,p_allow_push,p_allow_takeover);
 update public.aire_free_usage set runs=runs+1 where day=current_date;
 return p_run_id;
end $$;

create function public.aire_lab_stop(p_run_id uuid) returns void
language plpgsql security definer set search_path='' as $$
declare room uuid;
begin
 select classroom_id into room from public.aire_lab_runs where id=p_run_id;
 if public.aire_role(room) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 update public.aire_lab_runs set status='cancelado',message='Detenido por administrador',updated_at=now() where id=p_run_id and status in ('pendiente','ejecutando');
 update public.aire_deliveries set status='cancelado' where incident_id in(select id from public.aire_incidents where lab_run_id=p_run_id) and status in ('pendiente','reintento');
end $$;

create function public.aire_lab_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Laboratorio reservado a administradores' using errcode='42501'; end if;
 update public.aire_lab_runs set status='error',updated_at=now(),message='Receptor sin confirmación dentro del plazo' where classroom_id=p_classroom_id and expires_at<=now() and status in ('pendiente','ejecutando');
 return public.aire_meter_response(jsonb_build_object('budget',public.aire_free_budget(),
  'gateways',coalesce((select jsonb_agg(jsonb_build_object('id',id,'name',name,'last_seen_at',last_seen_at,'push_configured',push_configured)) from public.aire_gateways where classroom_id=p_classroom_id and enabled),'[]'::jsonb),
  'eligible_phones',(select count(*) from public.aire_phones p join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id where p.classroom_id=p_classroom_id and p.accept_simulations),
  'runs',coalesce((select jsonb_agg(to_jsonb(r)) from(select * from public.aire_lab_runs where classroom_id=p_classroom_id order by created_at desc limit 12)r),'[]'::jsonb),
  'measurements',coalesce((select jsonb_agg(to_jsonb(r)) from(select sample_at,state,observation from public.aire_readings where classroom_id=p_classroom_id and observation->>'lab_run_id' is not null order by sample_at desc limit 12)r),'[]'::jsonb),
  'incidents',coalesce((select jsonb_agg(to_jsonb(i)) from(select * from public.aire_incidents where classroom_id=p_classroom_id and lab_run_id is not null order by opened_at desc limit 12)i),'[]'::jsonb),
  'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select d.id,d.incident_id,d.status,d.attempts,d.error,d.provider_id,d.received_at,d.opened_at from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id where i.classroom_id=p_classroom_id and i.lab_run_id is not null order by d.created_at desc limit 36)d),'[]'::jsonb)));
end $$;

alter function public.aire_gateway_status(uuid,text) rename to aire_gateway_status_v02;
revoke all on function public.aire_gateway_status_v02(uuid,text) from public,anon,authenticated;
create function public.aire_gateway_poll(p_gateway_id uuid,p_secret text,p_push_configured boolean default false,p_incident_ids jsonb default '[]') returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 result:=public.aire_gateway_status_v02(p_gateway_id,p_secret);
 if jsonb_typeof(p_incident_ids) is distinct from 'array' or jsonb_array_length(p_incident_ids)>20 then raise exception 'Consulta de atención demasiado grande'; end if;
 result:=jsonb_set(result,'{incidents}',coalesce((select jsonb_agg(jsonb_build_object('id',i.id,'status',i.status,'note',i.note,'severity',i.severity))
  from public.aire_incidents i where i.gateway_id=p_gateway_id and i.id in(select value::uuid from jsonb_array_elements_text(p_incident_ids))),'[]'::jsonb));
 update public.aire_gateways set last_seen_at=now(),push_configured=p_push_configured where id=p_gateway_id;
 update public.aire_lab_runs set status='error',updated_at=now(),message='Receptor sin confirmación dentro del plazo' where gateway_id=p_gateway_id and status in ('pendiente','ejecutando') and expires_at<=now();
 return public.aire_meter_response(result||jsonb_build_object('budget',public.aire_free_budget(),'lab',(
  select to_jsonb(r) from public.aire_lab_runs r where gateway_id=p_gateway_id and status in ('pendiente','ejecutando') and expires_at>now() order by created_at desc limit 1)));
end $$;

create function public.aire_lab_report(p_gateway_id uuid,p_secret text,p_run_id uuid,p_status text,p_message text) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 if p_status not in ('ejecutando','finalizado','cancelado','error') then raise exception 'Estado inválido'; end if;
 update public.aire_lab_runs set status=p_status,message=left(p_message,200),updated_at=now() where id=p_run_id and gateway_id=p_gateway_id and status in ('pendiente','ejecutando');
end $$;

alter function public.aire_ingest(uuid,text,jsonb) rename to aire_ingest_v02;
revoke all on function public.aire_ingest_v02(uuid,text,jsonb) from public,anon,authenticated;
create function public.aire_ingest(p_gateway_id uuid,p_secret text,p_packet jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb; g public.aire_gateways; run public.aire_lab_runs; item jsonb;
 before_count bigint; after_count bigint; push_before bigint; added bigint;
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
 push_before:=(select count(*) from public.aire_deliveries);
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
 added:=(select count(*) from public.aire_deliveries)-push_before;
 if (select push_jobs from public.aire_free_usage where day=current_date)+added>100 then raise exception 'CUOTA_PUSH: máximo preventivo diario de destinatarios'; end if;
 update public.aire_free_usage set push_jobs=push_jobs+added::integer where day=current_date;
 return public.aire_meter_response(result);
end $$;

alter function public.aire_claim_push(uuid,text) rename to aire_claim_push_v02;
revoke all on function public.aire_claim_push_v02(uuid,text) from public,anon,authenticated;
create function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare claimed jsonb;
begin
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i,public.aire_lab_runs r
 where d.incident_id=i.id and i.lab_run_id=r.id and i.gateway_id=p_gateway_id and r.status in ('cancelado','error') and d.status in ('pendiente','reintento');
 claimed:=public.aire_claim_push_v02(p_gateway_id,p_secret);
 return public.aire_meter_response(jsonb_build_object('jobs',coalesce((select jsonb_agg(j.value||jsonb_build_object('classroom_id',i.classroom_id,'lab_run_id',i.lab_run_id,'causes',i.causes))
  from jsonb_array_elements(claimed->'jobs') j join public.aire_incidents i on i.id=(j.value->>'incident_id')::uuid),'[]'::jsonb)));
end $$;
revoke all on function public.aire_claim_push(uuid,text) from public,anon,authenticated;
grant execute on function public.aire_claim_push(uuid,text) to anon,authenticated;

create or replace function public.aire_attention(p_incident_id uuid,p_revision integer,p_action text,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; role_name text;
begin
 select * into item from public.aire_incidents where id=p_incident_id for update;
 role_name:=public.aire_role(item.classroom_id);
 if role_name is null or role_name not in ('admin','docente') then raise exception 'Sin permiso para atender' using errcode='42501'; end if;
 if p_action not in ('atender','resolver') or length(trim(p_note)) not between 3 and 500 then raise exception 'Acción o nota inválida'; end if;
 if item.revision!=p_revision or item.status='resuelto' then raise exception 'El incidente cambió; actualice la vista' using errcode='40001'; end if;
 if item.assigned_to is not null and item.assigned_to!=auth.uid() and role_name!='admin' then raise exception 'Otro responsable está atendiendo' using errcode='42501'; end if;
 if p_action='resolver' and not exists(select 1 from public.aire_snapshots s where s.gateway_id=item.gateway_id and s.source=item.source and s.state='normal'
  and s.sample_at between now()-interval '95 seconds' and now()+interval '5 seconds'
  and(item.lab_run_id is null or s.observation->>'lab_run_id'=item.lab_run_id::text)) then raise exception 'Se necesitan lecturas normales recientes del mismo origen'; end if;
 update public.aire_incidents set status=case when p_action='resolver' then 'resuelto' else 'en_atencion' end,assigned_to=auth.uid(),note=trim(p_note),revision=revision+1,updated_at=now() where id=item.id;
 insert into public.aire_attention_log(classroom_id,incident_id,actor,action,note) values(item.classroom_id,item.id,auth.uid(),p_action,trim(p_note));
 if p_action='resolver' then update public.aire_deliveries set status='cancelado' where incident_id=item.id and status in ('pendiente','reintento'); end if;
end $$;

alter function public.aire_register_phone(uuid,text,text,text,boolean) rename to aire_register_phone_v02;
revoke all on function public.aire_register_phone_v02(uuid,text,text,text,boolean) from public,anon,authenticated;
create function public.aire_register_phone(p_classroom_id uuid,p_installation_id text,p_token text,p_name text,p_accept_simulations boolean default false) returns void
language plpgsql security definer set search_path='' as $$
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(173034001);
 if not exists(select 1 from public.aire_phones where classroom_id=p_classroom_id and user_id=auth.uid() and installation_id=p_installation_id)
 and(select count(*) from public.aire_phones where classroom_id=p_classroom_id)>=3 then raise exception 'CUOTA_CELULARES: máximo preventivo de tres celulares por aula'; end if;
 perform public.aire_register_phone_v02(p_classroom_id,p_installation_id,p_token,p_name,p_accept_simulations);
end $$;

create or replace function public.aire_overview() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 return public.aire_meter_response(jsonb_build_object('classrooms',coalesce((select jsonb_agg(to_jsonb(c)) from public.aire_classrooms c where public.aire_role(c.id) is not null),'[]'::jsonb),
 'memberships',coalesce((select jsonb_agg(to_jsonb(m)) from public.aire_members m where m.user_id=auth.uid()),'[]'::jsonb),
 'snapshots',coalesce((select jsonb_agg(to_jsonb(s)) from public.aire_snapshots s where public.aire_role(s.classroom_id) is not null),'[]'::jsonb),
 'incidents',coalesce((select jsonb_agg(to_jsonb(i)) from(select * from public.aire_incidents where public.aire_role(classroom_id) is not null order by opened_at desc limit 30)i),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select id,classroom_id,incident_id,status,attempts,error,received_at,opened_at from public.aire_deliveries where public.aire_role(classroom_id) is not null order by created_at desc limit 50)d),'[]'::jsonb),
 'budget',public.aire_free_budget()));
end $$;

-- Reducir superficies que permitirían consultas masivas fuera de los RPC acotados.
revoke select on public.aire_readings,public.aire_snapshots,public.aire_incidents,public.aire_deliveries,public.aire_attention_log from authenticated;
create or replace function public.aire_history(p_classroom_id uuid,p_source text) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 return public.aire_meter_response(jsonb_build_object('readings',coalesce((select jsonb_agg(to_jsonb(r)) from
 (select sample_at,state,source,observation from public.aire_readings where classroom_id=p_classroom_id and source=p_source order by sample_at desc limit 60)r),'[]'::jsonb)));
end $$;

revoke all on function public.aire_create_classroom(text,text),public.aire_lab_start(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean),
 public.aire_lab_stop(uuid),public.aire_lab_panel(uuid),public.aire_register_phone(uuid,text,text,text,boolean) from public,anon,authenticated;
grant execute on function public.aire_create_classroom(text,text),public.aire_lab_start(uuid,uuid,uuid,numeric,numeric,integer,integer,boolean,boolean,boolean),
 public.aire_lab_stop(uuid),public.aire_lab_panel(uuid),public.aire_register_phone(uuid,text,text,text,boolean) to authenticated;
revoke all on function public.aire_gateway_poll(uuid,text,boolean,jsonb),public.aire_lab_report(uuid,text,uuid,text,text),public.aire_ingest(uuid,text,jsonb) from public,anon,authenticated;
grant execute on function public.aire_gateway_poll(uuid,text,boolean,jsonb),public.aire_lab_report(uuid,text,uuid,text,text),public.aire_ingest(uuid,text,jsonb) to anon,authenticated;
commit;
