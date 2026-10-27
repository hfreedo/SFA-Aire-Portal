-- Dispositivo estable y vínculo de sesión separados; compatibilidad RPC v1 conservada.
begin;
alter table public.aire_phones add column device_id text;
update public.aire_phones set device_id=installation_id where device_id is null;
alter table public.aire_phones alter column device_id set not null;

create function aire_private.register_phone(p_classroom_id uuid,p_device_id text,p_binding text,p_token text,p_name text,p_accept_simulations boolean) returns void
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
 and(select count(*) from public.aire_phones where classroom_id=p_classroom_id)>=3 then
  raise exception 'CUOTA_CELULARES: máximo preventivo de tres celulares por aula';
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

create or replace function public.aire_register_phone(p_classroom_id uuid,p_installation_id text,p_token text,p_name text,p_accept_simulations boolean default false) returns void
language sql security definer set search_path='' as $$
 select aire_private.register_phone(p_classroom_id,p_installation_id,p_installation_id,p_token,p_name,p_accept_simulations)
$$;
revoke all on function public.aire_register_phone(uuid,text,text,text,boolean) from public,anon,service_role;
grant execute on function public.aire_register_phone(uuid,text,text,text,boolean) to authenticated;

create function public.aire_register_phone_v2(p_classroom_id uuid,p_device_id uuid,p_binding uuid,p_token text,p_name text,p_accept_simulations boolean) returns void
language sql security definer set search_path='' as $$
 select aire_private.register_phone(p_classroom_id,p_device_id::text,p_binding::text,p_token,p_name,p_accept_simulations)
$$;
revoke all on function public.aire_register_phone_v2(uuid,uuid,uuid,text,text,boolean) from public,anon,service_role;
grant execute on function public.aire_register_phone_v2(uuid,uuid,uuid,text,text,boolean) to authenticated;

-- No admitir acuses sin acción ni resultados ambiguos del transporte PC.
create or replace function public.aire_receipt(p_delivery_id uuid,p_installation_id text,p_action text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if p_action is null or p_action not in ('recibido','abierto') then raise exception 'Acuse inválido'; end if;
 update public.aire_deliveries set received_at=coalesce(received_at,now()),
 opened_at=case when p_action='abierto' then coalesce(opened_at,now()) else opened_at end,status='recibido_app'
 where id=p_delivery_id and user_id=auth.uid() and installation_id=p_installation_id and public.aire_role(classroom_id) is not null;
 if not found then raise exception 'Entrega no autorizada' using errcode='42501'; end if;
end $$;
create function aire_private.validate_delivery_outcome(p_provider_id text,p_error text) returns void
language plpgsql set search_path='' as $$
begin
 if (p_provider_id is null)=(p_error is null) or (p_provider_id is not null and length(trim(p_provider_id))=0)
 or (p_error is not null and length(trim(p_error))=0) then raise exception 'Indique un resultado o error válido'; end if;
end $$;
revoke all on function aire_private.validate_delivery_outcome(text,text) from public,anon,authenticated,service_role;
alter function public.aire_finish_push(uuid,text,uuid,uuid,text,text) rename to aire_finish_push_v06;
revoke all on function public.aire_finish_push_v06(uuid,text,uuid,uuid,text,text) from public,anon,authenticated,service_role;
create function public.aire_finish_push(p_gateway_id uuid,p_secret text,p_delivery_id uuid,p_lease_id uuid,p_provider_id text default null,p_error text default null) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform aire_private.validate_delivery_outcome(p_provider_id,p_error);
 perform public.aire_finish_push_v06(p_gateway_id,p_secret,p_delivery_id,p_lease_id,p_provider_id,p_error);
end $$;
revoke all on function public.aire_finish_push(uuid,text,uuid,uuid,text,text) from public,service_role;
grant execute on function public.aire_finish_push(uuid,text,uuid,uuid,text,text) to anon,authenticated;
alter function public.aire_cloud_finish(uuid,uuid,text,text) rename to aire_cloud_finish_v06;
revoke all on function public.aire_cloud_finish_v06(uuid,uuid,text,text) from public,anon,authenticated,service_role;
create function public.aire_cloud_finish(p_delivery_id uuid,p_lease_id uuid,p_provider_id text default null,p_error text default null) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform aire_private.validate_delivery_outcome(p_provider_id,p_error);
 perform public.aire_cloud_finish_v06(p_delivery_id,p_lease_id,p_provider_id,p_error);
end $$;
revoke all on function public.aire_cloud_finish(uuid,uuid,text,text) from public,anon,authenticated;
grant execute on function public.aire_cloud_finish(uuid,uuid,text,text) to service_role;
commit;
