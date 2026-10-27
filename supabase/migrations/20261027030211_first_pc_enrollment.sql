-- Alta inicial de una PC limpia, sin compartir secretos de otra instalación.
begin;
create function public.aire_enroll_pc(p_classroom_id uuid,p_origin_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways;
begin
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula' using errcode='42501'; end if;
 if p_origin_id is null or p_secret is null or length(p_secret) not between 40 and 200 then raise exception 'Identidad de PC inválida'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into g from public.aire_gateways where enabled and kind='pc' and origin_id=p_origin_id limit 1;
 if g.id is not null then
  if g.classroom_id is distinct from p_classroom_id or g.secret_hash is distinct from sha256(convert_to(p_secret,'UTF8')) then raise exception 'Esta identidad ya está vinculada. Use su configuración local' using errcode='42501'; end if;
  return jsonb_build_object('classroom_id',g.classroom_id,'gateway_id',g.id);
 end if;
 if (select count(*) from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc')>=2 then raise exception 'CUOTA_RECEPTORES: el aula ya tiene dos PC. Revise PC del aula en Administración'; end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: límite preventivo de tamaño'; end if;
 insert into public.aire_gateways(classroom_id,name,secret_hash,origin_id) values(p_classroom_id,'PC del aula',sha256(convert_to(p_secret,'UTF8')),p_origin_id) returning * into g;
 return jsonb_build_object('classroom_id',g.classroom_id,'gateway_id',g.id);
end $$;
revoke all on function public.aire_enroll_pc(uuid,uuid,text) from public,anon,authenticated,service_role;
grant execute on function public.aire_enroll_pc(uuid,uuid,text) to authenticated;
commit;
