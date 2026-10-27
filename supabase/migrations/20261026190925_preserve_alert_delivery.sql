-- Atención humana y entrega independientes. No reabre entregas ya canceladas.
begin;
create or replace function public.aire_attention(p_incident_id uuid,p_revision integer,p_action text,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; message text:=trim(coalesce(p_note,'')); stored_note text;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=p_incident_id for update;
 if auth.uid() is null or not coalesce(public.aire_role(item.classroom_id) in ('admin','docente'),false) then
  raise exception 'Sin permiso de atención en esta aula' using errcode='42501';
 end if;
 if p_action is null or p_action not in ('atender','resolver') or length(message)>500 then
  raise exception 'Acción inválida o nota superior a 500 caracteres';
 end if;
 -- Reintento tras respuesta perdida: no duplica historial ni cambia al actor.
 if p_action='resolver' and item.status='resuelto' and item.closure_kind='atendido'
  and item.closed_by=auth.uid() and item.closure_reason=message and p_revision=item.revision-1 then return; end if;
 if item.revision is distinct from p_revision or item.status='resuelto' then
  raise exception 'El aviso cambió; actualice el estado' using errcode='40001';
 end if;
 stored_note:=case when p_action='resolver' then 'AVISO ATENDIDO · No confirma normalización del ambiente.'||case when message<>'' then ' '||message else '' end else message end;
 update public.aire_incidents set status=case when p_action='resolver' then 'resuelto' else 'en_atencion' end,
  assigned_to=auth.uid(),note=stored_note,revision=revision+1,updated_at=now(),
  closure_kind=case when p_action='resolver' then 'atendido' else closure_kind end,
  closed_by=case when p_action='resolver' then auth.uid() else closed_by end,
  closed_at=case when p_action='resolver' then now() else closed_at end,
  closure_reason=case when p_action='resolver' then message else closure_reason end where id=item.id;
 insert into public.aire_attention_log(classroom_id,incident_id,actor,action,note)
 values(item.classroom_id,item.id,auth.uid(),p_action,stored_note);
 if p_action='resolver' then
  -- Indicaciones antiguas no bloquean; se conservan sin afirmar ejecución.
  update public.aire_instructions set status='reemplazada',revision=revision+1
   where incident_id=item.id and status not in ('realizada','reemplazada');
  update public.aire_deliveries set status='cancelado',lease_id=null,lease_until=null
   where incident_id=item.id and event_id is not null and status in ('pendiente','reintento');
 end if;
 -- Sin comunicaciones ni nuevas notificaciones de coordinación implícitas.
end $$;
create or replace function public.aire_cloud_claim_v06() returns jsonb
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
 (i.status='resuelto' and d.event_id is not null) or not exists(select 1 from public.aire_gateways g where g.id=i.gateway_id and g.enabled)
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
create or replace function public.aire_claim_push_v02(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways; result jsonb;
begin
 select * into g from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8'));
 if not found then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 update public.aire_deliveries d set status='vencido' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and d.created_at<now()-interval '5 minutes';
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and ((i.status='resuelto' and d.event_id is not null) or not exists(select 1 from public.aire_members m where m.classroom_id=d.classroom_id and m.user_id=d.user_id));
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
create or replace function aire_private.register_phone(p_classroom_id uuid,p_device_id text,p_binding text,p_token text,p_name text,p_accept_simulations boolean) returns void
language plpgsql set search_path='' as $$
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 if p_device_id is null or length(p_device_id) not between 8 and 120
 or p_binding is null or length(p_binding) not between 8 and 120
 or p_token is null or length(p_token) not between 20 and 4096
 or p_name is null or length(trim(p_name)) not between 1 and 100
 or p_accept_simulations is null then raise exception 'Dispositivo inválido'; end if;
 perform pg_advisory_xact_lock(173034001);
 -- Salida offline, cambio de cuenta, reinstalación o rotación de token: un teléfono
 -- solo conserva la identidad y vínculo que acaba de registrar explícitamente.
 with retired as (
  delete from public.aire_phones
  where (device_id=p_device_id or token=p_token)
    and (user_id<>auth.uid() or installation_id<>p_binding)
  returning classroom_id,user_id,installation_id
 ) update public.aire_deliveries d set status='cancelado',lease_id=null,lease_until=null
 where d.status in ('pendiente','reintento') and exists(
  select 1 from retired r where r.classroom_id=d.classroom_id and r.user_id=d.user_id and r.installation_id=d.installation_id);
 if not exists(select 1 from public.aire_phones where classroom_id=p_classroom_id and user_id=auth.uid() and installation_id=p_binding)
 and(select count(*) from public.aire_phones where classroom_id=p_classroom_id)>=20 then
  raise exception 'CUOTA_CELULARES: máximo preventivo de veinte teléfonos por aula';
 end if;
 if not exists(select 1 from public.aire_phones where classroom_id=p_classroom_id and user_id=auth.uid() and installation_id=p_binding)
 and(select count(*) from public.aire_phones where classroom_id=p_classroom_id and user_id=auth.uid())>=2 then
  raise exception 'CUOTA_CUENTA: máximo preventivo de dos teléfonos por persona y aula';
 end if;
 -- La rotación de token conserva las otras aulas registradas de la misma sesión.
 update public.aire_phones set token=p_token,updated_at=now()
 where device_id=p_device_id and user_id=auth.uid() and installation_id=p_binding;
 insert into public.aire_phones(classroom_id,user_id,installation_id,token,name,accept_simulations,updated_at,device_id)
 values(p_classroom_id,auth.uid(),p_binding,p_token,trim(p_name),p_accept_simulations,now(),p_device_id)
 on conflict(classroom_id,user_id,installation_id) do update set
 token=excluded.token,name=excluded.name,accept_simulations=excluded.accept_simulations,
 updated_at=excluded.updated_at,device_id=excluded.device_id;
end $$;
revoke all on function aire_private.register_phone(uuid,text,text,text,text,boolean) from public,anon,authenticated,service_role;
revoke all on function public.aire_cloud_claim_v06(),public.aire_claim_push_v02(uuid,text) from public,anon,authenticated,service_role;
commit;
