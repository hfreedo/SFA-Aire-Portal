-- Verificación MVCC: la lectura debe pertenecer a esta transacción.
create or replace function aire_private.capture_incident_reading() returns trigger
language plpgsql security definer set search_path='' as $$
declare r public.aire_readings;
begin
 if TG_OP='UPDATE' and not(old.severity='aviso' and new.severity='alerta') then return new;end if;
 select * into r from public.aire_readings as reading where gateway_id=new.gateway_id
  and classroom_id=new.classroom_id and source=new.source
  and reading.xmin::text::bigint = (txid_current() % 4294967296)
  and ingested_at=transaction_timestamp() order by id desc limit 1;
 if found then
  new.trigger_sample_at:=r.sample_at;
  new.trigger_observation:=jsonb_build_object('temperature',r.observation->'temperature',
   'humidity',r.observation->'humidity','mq_raw',r.observation->'mq_raw',
   'dht_ok',r.observation->'dht_ok','notification_test',coalesce(r.observation->'notification_test','false'::jsonb));
 end if;
 return new;
end $$;
