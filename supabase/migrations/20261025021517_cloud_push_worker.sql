-- v0.6: emisor independiente de PC. RPC del worker solo para service_role.
begin;
create schema if not exists aire_private;
revoke all on schema aire_private from public,anon,authenticated;
create table aire_private.push_worker (
 id boolean primary key default true check(id), enabled boolean not null default false,
 endpoint text, worker_secret_id uuid, firebase_secret_id uuid,
 last_dispatch timestamptz, last_auth_ok timestamptz, last_error text,
 cooldown_until timestamptz, updated_at timestamptz not null default now());
insert into aire_private.push_worker(id) values(true);
create table aire_private.push_worker_usage (
 day date primary key, dispatches integer not null default 0, invocations integer not null default 0);
alter table aire_private.push_worker enable row level security;
alter table aire_private.push_worker_usage enable row level security;
revoke all on all tables in schema aire_private from public,anon,authenticated;

create function public.aire_cloud_configure(p_account jsonb,p_endpoint text,p_confirm_free boolean) returns jsonb
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; key_id uuid; worker_id uuid;
begin
 if p_confirm_free is distinct from true then raise exception 'Confirme Free / Spark sin Billing'; end if;
 if p_account->>'type' is distinct from 'service_account' or p_account->>'project_id' is distinct from 'sfa-aire-aulas'
 or not coalesce(p_account->>'client_email' like '%@sfa-aire-aulas.iam.gserviceaccount.com',false)
 or not coalesce(p_account->>'private_key' like '-----BEGIN PRIVATE KEY-----%',false) then raise exception 'Cuenta de servicio incorrecta'; end if;
 if p_endpoint is null or p_endpoint !~ '^https://[a-z0-9]{20}\.supabase\.co/functions/v1/aire-push$' then raise exception 'Endpoint no permitido'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into w from aire_private.push_worker where id for update;
 if w.firebase_secret_id is null then
  select vault.create_secret(p_account::text,'aire_firebase_service_account') into key_id;
 else
  perform vault.update_secret(w.firebase_secret_id,p_account::text); key_id:=w.firebase_secret_id;
 end if;
 worker_id:=w.worker_secret_id;
 if worker_id is null then
  select vault.create_secret(replace(gen_random_uuid()::text,'-','')||replace(gen_random_uuid()::text,'-',''),'aire_push_worker_token') into worker_id;
 end if;
 update aire_private.push_worker set enabled=true,endpoint=p_endpoint,worker_secret_id=worker_id,
  firebase_secret_id=key_id,last_error=null,last_auth_ok=null,cooldown_until=null,updated_at=now() where id;
 return jsonb_build_object('configured',true,'firebase_project','sfa-aire-aulas');
end $$;

create function public.aire_cloud_open(p_worker_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; expected text; account jsonb; calls integer;
begin
 select * into w from aire_private.push_worker where id for update;
 select decrypted_secret into expected from vault.decrypted_secrets where id=w.worker_secret_id;
 if length(p_worker_secret) is distinct from 64 or expected is null
 or sha256(convert_to(p_worker_secret,'UTF8'))<>sha256(convert_to(expected,'UTF8')) then
  return jsonb_build_object('authorized',false);
 end if;
 if not w.enabled then return jsonb_build_object('authorized',true,'ready',false,'state','disabled'); end if;
 insert into aire_private.push_worker_usage(day) values(current_date) on conflict do nothing;
 select invocations into calls from aire_private.push_worker_usage where day=current_date;
 if calls>=600 or (select sum(invocations) from aire_private.push_worker_usage where day>=date_trunc('month',now())::date)>=10000 then
  return jsonb_build_object('authorized',true,'ready',false,'state','preventive_limit');
 end if;
 update aire_private.push_worker_usage set invocations=invocations+1 where day=current_date;
 select decrypted_secret::jsonb into account from vault.decrypted_secrets where id=w.firebase_secret_id;
 return jsonb_build_object('authorized',true,'ready',account is not null,'state','configured','account',account);
end $$;

create function public.aire_cloud_health(p_error text) returns void
language plpgsql security definer set search_path='' as $$
begin
 update aire_private.push_worker set last_error=left(p_error,80),
 last_auth_ok=case when p_error is null then now() else last_auth_ok end,
 cooldown_until=case when p_error is not null then now()+interval '5 minutes' else null end,updated_at=now() where id;
end $$;

create function public.aire_cloud_claim() returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 perform pg_advisory_xact_lock(173034001);
 if not exists(select 1 from aire_private.push_worker where id and enabled and last_auth_ok is not null and last_error is null) then
  return jsonb_build_object('jobs','[]'::jsonb);
 end if;
 -- Un destinatario revocado, teléfono retirado u orden vencida nunca se reenvía.
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i
 where i.id=d.incident_id and d.status in ('pendiente','reintento') and (
 i.status='resuelto' or not exists(select 1 from public.aire_gateways g where g.id=i.gateway_id and g.enabled)
 or not exists(select 1 from public.aire_members m where m.classroom_id=d.classroom_id and m.user_id=d.user_id)
 or not exists(select 1 from public.aire_phones p where p.classroom_id=d.classroom_id and p.user_id=d.user_id and p.installation_id=d.installation_id and (i.source='arduino' or p.accept_simulations))
 or (i.source='simulacion' and not exists(select 1 from public.aire_lab_runs r join public.aire_members m on m.classroom_id=r.classroom_id and m.user_id=r.created_by and m.role='admin'
    where r.id=i.lab_run_id and r.allow_push and r.status not in ('cancelado','error')))
 or (d.event_id is not null and (not exists(select 1 from public.aire_duty t where t.classroom_id=d.classroom_id and d.user_id in (t.coordinator,t.teacher,t.deputy))
    or exists(select 1 from public.aire_coord_events e join public.aire_instructions x on x.id=e.instruction_id where e.id=d.event_id and (x.status='reemplazada' or x.expires_at<=now())))));
 update public.aire_deliveries set status='vencido',lease_id=null,lease_until=null
 where status in ('pendiente','reintento') and created_at<now()-interval '5 minutes' and (lease_until is null or lease_until<now());
 update public.aire_deliveries set status='error',error='WorkerLeaseExhausted',lease_id=null,lease_until=null
 where status in ('pendiente','reintento') and attempts>=5 and lease_until<now();
 with jobs as (
  select d.id from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id
  where d.status in ('pendiente','reintento') and d.next_try<=now() and d.attempts<5
   and (d.lease_until is null or d.lease_until<now())
  order by case when i.source='arduino' then 0 else 1 end,d.created_at,d.id limit 9 for update of d skip locked
 ), claimed as (
  update public.aire_deliveries d set lease_id=gen_random_uuid(),lease_until=now()+interval '120 seconds',attempts=attempts+1
  where id in(select id from jobs) returning d.*
 ) select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'lease_id',d.lease_id,'incident_id',i.id,
 'classroom_id',d.classroom_id,'severity',i.severity,'source',i.source,'token',p.token,
 'lab_run_id',i.lab_run_id,'causes',i.causes,'event_id',d.event_id,'event_kind',e.kind)
 order by case when i.source='arduino' then 0 else 1 end,d.created_at,d.id),'[]'::jsonb) into result
 from claimed d join public.aire_incidents i on i.id=d.incident_id
 join public.aire_phones p on p.classroom_id=d.classroom_id and p.user_id=d.user_id and p.installation_id=d.installation_id
 left join public.aire_coord_events e on e.id=d.event_id;
 return jsonb_build_object('jobs',result);
end $$;

create function public.aire_cloud_finish(p_delivery_id uuid,p_lease_id uuid,p_provider_id text default null,p_error text default null) returns void
language plpgsql security definer set search_path='' as $$
begin
 if (p_provider_id is null)=(p_error is null) then raise exception 'Indique resultado o error'; end if;
 update public.aire_deliveries set status=case when received_at is not null then 'recibido_app'
 when status='cancelado' then 'cancelado' when p_error is null then 'aceptado_fcm'
 when attempts>=5 or p_error in ('UnregisteredError','SenderIdMismatchError','InvalidMessageError') then 'error' else 'reintento' end,
 provider_id=left(p_provider_id,250),error=left(p_error,100),
 next_try=now()+make_interval(secs=>least(300,power(2,attempts)::integer*5)),lease_id=null,lease_until=null
 where id=p_delivery_id and lease_id=p_lease_id;
 if not found then raise exception 'Lease de entrega inválido'; end if;
end $$;

-- Solo el emisor activo puede reclamar; una PC anterior no duplica el envío.
alter function public.aire_claim_push(uuid,text) rename to aire_claim_push_v05;
revoke all on function public.aire_claim_push_v05(uuid,text) from public,anon,authenticated;
create function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 perform pg_advisory_xact_lock(173034001);
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 if exists(select 1 from aire_private.push_worker where id and enabled) then return jsonb_build_object('jobs','[]'::jsonb,'transport','cloud'); end if;
 return public.aire_claim_push_v05(p_gateway_id,p_secret);
end $$;
revoke all on function public.aire_claim_push(uuid,text) from public;
grant execute on function public.aire_claim_push(uuid,text) to anon,authenticated;

alter function public.aire_gateway_poll(uuid,text,boolean,jsonb) rename to aire_gateway_poll_v05;
revoke all on function public.aire_gateway_poll_v05(uuid,text,boolean,jsonb) from public,anon,authenticated;
create function public.aire_gateway_poll(p_gateway_id uuid,p_secret text,p_push_configured boolean default false,p_incident_ids jsonb default '[]') returns jsonb
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; result jsonb;
begin
 select * into w from aire_private.push_worker where id;
 result:=public.aire_gateway_poll_v05(p_gateway_id,p_secret,
 case when w.enabled then w.last_auth_ok is not null and w.last_error is null else p_push_configured end,p_incident_ids);
 return result||jsonb_build_object('push_transport',case when w.enabled then 'cloud' else 'pc' end,
  'push_worker',jsonb_build_object('enabled',w.enabled,'last_auth_ok',w.last_auth_ok,'error',w.last_error));
end $$;
revoke all on function public.aire_gateway_poll(uuid,text,boolean,jsonb) from public;
grant execute on function public.aire_gateway_poll(uuid,text,boolean,jsonb) to anon,authenticated;

create function public.aire_cloud_status(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores' using errcode='42501'; end if;
 select jsonb_build_object('transport',case when enabled then 'cloud' else 'pc' end,'configured',firebase_secret_id is not null,
 'last_auth_ok',last_auth_ok,'last_error',last_error,'last_dispatch',last_dispatch,
 'invocations_today',coalesce((select invocations from aire_private.push_worker_usage where day=current_date),0),
 'invocations_month',coalesce((select sum(invocations) from aire_private.push_worker_usage where day>=date_trunc('month',now())::date),0),
 'daily_limit',600,'monthly_limit',10000) into result from aire_private.push_worker where id;
 return result;
end $$;
revoke all on function public.aire_cloud_status(uuid) from public,anon;
grant execute on function public.aire_cloud_status(uuid) to authenticated;

alter function public.aire_lab_panel(uuid) rename to aire_lab_panel_v05;
revoke all on function public.aire_lab_panel_v05(uuid) from public,anon,authenticated;
create function public.aire_lab_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 return public.aire_lab_panel_v05(p_classroom_id)||jsonb_build_object('cloud_worker',public.aire_cloud_status(p_classroom_id));
end $$;
revoke all on function public.aire_lab_panel(uuid) from public,anon;
grant execute on function public.aire_lab_panel(uuid) to authenticated;

revoke all on function public.aire_cloud_configure(jsonb,text,boolean),public.aire_cloud_open(text),
 public.aire_cloud_health(text),public.aire_cloud_claim(),public.aire_cloud_finish(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.aire_cloud_configure(jsonb,text,boolean),public.aire_cloud_open(text),
 public.aire_cloud_health(text),public.aire_cloud_claim(),public.aire_cloud_finish(uuid,uuid,text,text) to service_role;
commit;
