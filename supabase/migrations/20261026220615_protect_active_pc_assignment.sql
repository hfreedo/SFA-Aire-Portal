-- Asignación desde la PC autenticada; no cambia ni revoca otras instalaciones.
begin;
create or replace function public.aire_assign_pc(p_classroom_id uuid,p_origin_id uuid,p_secret text,
 p_previous_gateway_id uuid,p_previous_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways; previous public.aire_gateways;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador del aula destino' using errcode='42501'; end if;
 if p_origin_id is null or p_secret is null or length(p_secret) not between 40 and 200 then raise exception 'Identidad de PC inválida'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into previous from public.aire_gateways where id=p_previous_gateway_id and enabled and kind='pc'
  and secret_hash=sha256(convert_to(p_previous_secret,'UTF8'));
 if previous.id is null or public.aire_role(previous.classroom_id) is distinct from 'admin' then
  raise exception 'Verifique la administración del aula actual de esta PC' using errcode='42501';
 end if;
 select * into g from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc'
  and origin_id=p_origin_id and secret_hash=sha256(convert_to(p_secret,'UTF8')) limit 1;
 if g.id is null then
  select * into g from public.aire_gateways candidate where classroom_id=p_classroom_id and enabled and kind='pc'
   and origin_id is null and last_seq=0 and last_seen_at is null
   and not exists(select 1 from public.aire_readings where gateway_id=candidate.id)
   and not exists(select 1 from public.aire_incidents where gateway_id=candidate.id)
   and not exists(select 1 from public.aire_lab_runs where gateway_id=candidate.id)
   order by (name ilike 'PC%') desc,id limit 1 for update;
  if g.id is null then
   if (select count(*) from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc')>=2 then
    raise exception 'CUOTA_RECEPTORES: el aula ya tiene dos PC vinculadas. Retire una desde Administración';
   end if;
   if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: límite preventivo de tamaño'; end if;
   insert into public.aire_gateways(classroom_id,name,secret_hash,origin_id)
    values(p_classroom_id,'PC del aula',sha256(convert_to(p_secret,'UTF8')),p_origin_id) returning * into g;
  else
   update public.aire_gateways set secret_hash=sha256(convert_to(p_secret,'UTF8')),origin_id=p_origin_id,revision=revision+1
    where id=g.id returning * into g;
  end if;
 end if;
 return jsonb_build_object('gateway_id',g.id,'classroom_id',g.classroom_id,'name',g.name);
end $$;
revoke all on function public.aire_assign_pc(uuid,uuid,text,uuid,text) from public,anon,service_role;
grant execute on function public.aire_assign_pc(uuid,uuid,text,uuid,text) to authenticated;
commit;
