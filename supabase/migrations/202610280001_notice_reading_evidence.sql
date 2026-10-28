-- Evidencia acotada del paquete que crea/eleva el aviso; nunca usa la última
-- lectura de otra transacción ni rellena incidentes históricos por aproximación.
alter table public.aire_incidents add column trigger_observation jsonb,
 add column trigger_sample_at timestamptz;
create function aire_private.capture_incident_reading() returns trigger
language plpgsql security definer set search_path='' as $$
declare r public.aire_readings;
begin
 if TG_OP='UPDATE' and not(old.severity='aviso' and new.severity='alerta') then return new;end if;
 select * into r from public.aire_readings where gateway_id=new.gateway_id
  and classroom_id=new.classroom_id and source=new.source
  and ingested_at=transaction_timestamp() order by id desc limit 1;
 if found then
  new.trigger_sample_at:=r.sample_at;
  new.trigger_observation:=jsonb_build_object('temperature',r.observation->'temperature',
   'humidity',r.observation->'humidity','mq_raw',r.observation->'mq_raw',
   'dht_ok',r.observation->'dht_ok','notification_test',coalesce(r.observation->'notification_test','false'::jsonb));
 end if;
 return new;
end $$;
revoke all on function aire_private.capture_incident_reading() from public,anon,authenticated,service_role;
create trigger aire_incident_reading before insert or update of severity on public.aire_incidents
 for each row execute function aire_private.capture_incident_reading();

-- Campos opcionales, compatibles con contrato FCM 2 y los clientes anteriores.
create or replace function aire_private.bind_notification_jobs(p_result jsonb) returns jsonb
language sql stable set search_path='' as $$
 select p_result || jsonb_build_object('jobs',coalesce((select jsonb_agg(j.value || jsonb_build_object(
 'installation_id',d.installation_id,'notification_test',coalesce(r.execution_kind='cloud_notification',false),
 'classroom_name',left(c.name,100),'observation',i.trigger_observation,'sample_at',i.trigger_sample_at)
 order by j.ordinality)
 from jsonb_array_elements(p_result->'jobs') with ordinality j(value,ordinality)
 join public.aire_deliveries d on d.id=(j.value->>'id')::uuid
 join public.aire_incidents i on i.id=d.incident_id
 join public.aire_classrooms c on c.id=i.classroom_id
 left join public.aire_lab_runs r on r.id=i.lab_run_id),'[]'::jsonb))
$$;
revoke all on function aire_private.bind_notification_jobs(jsonb) from public,anon,authenticated,service_role;
