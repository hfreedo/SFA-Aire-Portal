-- Una escalada reciente debe notificar aunque el aviso inicial tenga más de 60 s.
-- Se conserva la exclusión de incidentes históricos y la deduplicación por gravedad.
begin;
create or replace function public.aire_ingest_v02(p_gateway_id uuid,p_secret text,p_packet jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways; item jsonb; incident public.aire_incidents;
 seq bigint; observed timestamptz; src text; st text; opened timestamptz; sev text; changed boolean; payload jsonb;
begin
 select * into g from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8')) for update;
 if not found then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 if octet_length(p_packet::text)>100000 then raise exception 'Paquete demasiado grande'; end if;
 if g.origin_id is not null and g.origin_id!=(p_packet->>'origin_id')::uuid then raise exception 'El receptor ya pertenece a otra instalación'; end if;
 seq:=(p_packet->>'seq')::bigint;
 if seq<=0 or (p_packet->>'origin_id') is null then raise exception 'Secuencia/origen inválidos'; end if;
 if seq>g.last_seq then
  src:=p_packet->>'source'; st:=p_packet->>'state'; observed:=to_timestamp((p_packet->>'sample_at')::double precision);
  payload:=p_packet->'observation';
  if src is null or src not in ('arduino','simulacion') or st is null or st not in ('normal','aviso','alerta','calentando','sin_calibrar','fallo_sensor')
   or observed is null or observed>now()+interval '5 minutes' or observed<now()-interval '30 days'
   or jsonb_typeof(payload) is distinct from 'object' or (payload->>'mq_raw') is null
   or (payload->>'mq_raw')::numeric not between 0 and 1023 then raise exception 'Medición inválida o reloj fuera de rango'; end if;
  insert into public.aire_readings(classroom_id,gateway_id,seq,source,sample_at,state,observation)
   values(g.classroom_id,g.id,seq,src,observed,st,payload);
  insert into public.aire_snapshots values(g.id,src,g.classroom_id,observed,now(),st,payload)
   on conflict(gateway_id,source) do update set sample_at=excluded.sample_at,ingested_at=now(),state=excluded.state,observation=excluded.observation
   where excluded.sample_at>=public.aire_snapshots.sample_at;
  if jsonb_typeof(p_packet->'incidents') is distinct from 'array' or jsonb_array_length(p_packet->'incidents')>10 then raise exception 'Lista de incidentes inválida'; end if;
  for item in select value from jsonb_array_elements(p_packet->'incidents') loop
   sev:=item->>'severity'; opened:=to_timestamp((item->>'opened')::double precision);
   if (item->>'source') is distinct from src or sev is null or sev not in ('aviso','alerta') or opened is null or opened>observed+interval '5 minutes' then raise exception 'Incidente inválido'; end if;
   select * into incident from public.aire_incidents where id=(item->>'id')::uuid for update;
   changed:=false;
   if not found then
    insert into public.aire_incidents(id,classroom_id,gateway_id,source,severity,opened_at,historical)
     values((item->>'id')::uuid,g.classroom_id,g.id,src,sev,opened,opened<now()-interval '60 seconds') returning * into incident;
    changed:=true;
   else
    if incident.gateway_id!=g.id or incident.source!=src then raise exception 'Colisión de identificador de incidente'; end if;
    if incident.status!='resuelto' and incident.severity='aviso' and sev='alerta' then
     update public.aire_incidents set severity='alerta',revision=revision+1,updated_at=now() where id=incident.id returning * into incident;
     changed:=true;
    end if;
   end if;
   if changed and not incident.historical and observed>=now()-interval '60 seconds' then
    insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity)
     select g.classroom_id,incident.id,p.user_id,p.installation_id,sev from public.aire_phones p
     join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id
     where p.classroom_id=g.classroom_id and (src!='simulacion' or p.accept_simulations)
     on conflict(incident_id,user_id,installation_id,severity) do nothing;
   end if;
  end loop;
  update public.aire_gateways set last_seq=seq,origin_id=(p_packet->>'origin_id')::uuid where id=g.id;
 end if;
 return jsonb_build_object('accepted_seq',greatest(seq,g.last_seq),'incidents',coalesce((
  select jsonb_agg(jsonb_build_object('id',i.id,'status',i.status,'note',i.note,'severity',i.severity))
  from public.aire_incidents i where i.gateway_id=g.id and i.id in (select (value->>'id')::uuid from jsonb_array_elements(p_packet->'incidents'))),'[]'::jsonb));
end $$;
commit;
