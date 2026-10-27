-- Infraestructura alojada. No usa Google Cloud Functions ni Cloud Scheduler.
begin;
create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron;

create function aire_private.dispatch_push(p_force boolean default false) returns bigint
language plpgsql security definer set search_path='' as $$
declare w aire_private.push_worker; token text; request_id bigint;
begin
 select * into w from aire_private.push_worker where id for update;
 if not w.enabled or w.worker_secret_id is null or w.firebase_secret_id is null or w.endpoint is null
  or w.cooldown_until>now() or w.last_dispatch>now()-interval '10 seconds' then return null; end if;
 if not p_force and w.last_auth_ok is not null and w.last_error is null and not exists(
  select 1 from public.aire_deliveries where status in ('pendiente','reintento') and next_try<=now()
  and (lease_until is null or lease_until<now())) then return null; end if;
 insert into aire_private.push_worker_usage(day) values(current_date) on conflict do nothing;
 if (select dispatches from aire_private.push_worker_usage where day=current_date)>=600
 or (select sum(dispatches) from aire_private.push_worker_usage where day>=date_trunc('month',now())::date)>=10000 then return null; end if;
 select decrypted_secret into token from vault.decrypted_secrets where id=w.worker_secret_id;
 if token is null then return null; end if;
 select net.http_post(url:=w.endpoint,headers:=jsonb_build_object('Content-Type','application/json','x-sfa-worker',token),
  body:='{}'::jsonb,timeout_milliseconds:=5000) into request_id;
 update aire_private.push_worker set last_dispatch=now() where id;
 update aire_private.push_worker_usage set dispatches=dispatches+1 where day=current_date;
 return request_id;
end $$;
revoke all on function aire_private.dispatch_push(boolean) from public,anon,authenticated;

create function aire_private.wake_push() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 -- La cola y el incidente se confirman aunque la infraestructura de wake falle.
 begin perform aire_private.dispatch_push(); exception when others then
  update aire_private.push_worker set last_error='SchedulerDispatchError',cooldown_until=now()+interval '1 minute' where id;
 end;
 return null;
end $$;
revoke all on function aire_private.wake_push() from public,anon,authenticated;
create trigger aire_cloud_wake after insert on public.aire_deliveries
 for each statement execute function aire_private.wake_push();

select cron.schedule('aire-push-retry','* * * * *',$cron$select aire_private.dispatch_push();$cron$);
-- Mantener acotado el historial propio de cron; no borra el historial del aula.
select cron.schedule('aire-push-cron-retention','17 3 * * *',$cron$
 delete from cron.job_run_details where jobid in(select jobid from cron.job where jobname in ('aire-push-retry','aire-push-cron-retention')) and end_time<now()-interval '2 days';
$cron$);
commit;
