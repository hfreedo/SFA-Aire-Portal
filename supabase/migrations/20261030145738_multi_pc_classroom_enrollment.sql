-- Margen para ensayos escolares en varias PC; consumo y autorizaciones conservados.
begin;
create or replace function aire_private.pc_registration_limit() returns integer
language sql immutable set search_path='' as $$ select 10 $$;
revoke all on function aire_private.pc_registration_limit() from public,anon,authenticated,service_role;

CREATE OR REPLACE FUNCTION public.aire_admin_capabilities(p_classroom_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare role_name text; creator boolean; owner boolean; rooms integer; active_count integer;
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 role_name:=public.aire_role(p_classroom_id);
 if p_classroom_id is not null and role_name is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 creator:=exists(select 1 from public.aire_creators where user_id=auth.uid());
 owner:=exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid());
 select count(*) into rooms from public.aire_classrooms;
 select count(*) into active_count from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id and enabled;
 return public.aire_meter_response(jsonb_build_object(
  'classroom_id',p_classroom_id,'can_create_classroom',creator and rooms<3,
  'can_manage_members',coalesce(role_name='admin',false),'can_manage_gateways',coalesce(role_name='admin',false),
  'create_reason',case when not creator then 'Esta cuenta no está habilitada para crear aulas' when rooms>=3 then 'Se alcanzó el máximo preventivo de tres aulas' else null end,
  'members_reason',case when role_name is distinct from 'admin' then 'Solo administradores del aula pueden gestionar personas' else null end,
  'gateway_limit',aire_private.pc_registration_limit(),'active_gateways',active_count,
  'gateway_total',(select count(*) from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id),
  'gateways',case when role_name='admin' then coalesce((select jsonb_agg(jsonb_build_object(
    'id',id,'name',name,'enabled',enabled,'revision',revision,'last_seen_at',last_seen_at,'paired',origin_id is not null,'revoked_at',revoked_at,'revoked_by',revoked_by,'revoked_reason',revoked_reason)
    order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id) from (select * from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id limit 50) listed),'[]'::jsonb) else '[]'::jsonb end));
end $function$
;

CREATE OR REPLACE FUNCTION public.aire_assign_pc(p_classroom_id uuid, p_origin_id uuid, p_secret text, p_previous_gateway_id uuid, p_previous_secret text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
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
   if (select count(*) from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc')>=aire_private.pc_registration_limit() then
    raise exception 'CUOTA_RECEPTORES: se alcanzaron las 10 PC habilitadas de esta aula. Retire solo equipos que ya no se utilicen';
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
end $function$
;

CREATE OR REPLACE FUNCTION public.aire_create_gateway(p_classroom_id uuid, p_name text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare secret text; gateway uuid;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 if p_name is null or length(trim(p_name)) not between 2 and 100 then raise exception 'Nombre de receptor inválido'; end if;
 perform pg_advisory_xact_lock(173034001);
 if (select count(*) from public.aire_gateways where kind='pc' and classroom_id=p_classroom_id and enabled)>=aire_private.pc_registration_limit() then
  raise exception 'CUOTA_RECEPTORES: se alcanzaron las 10 PC habilitadas de esta aula. Retire solo equipos que ya no se utilicen';
 end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: se alcanzó la guarda preventiva de tamaño'; end if;
 secret:=gen_random_uuid()::text||gen_random_uuid()::text;
 insert into public.aire_gateways(classroom_id,name,secret_hash)
 values(p_classroom_id,trim(p_name),sha256(convert_to(secret,'UTF8'))) returning id into gateway;
 return jsonb_build_object('gateway_id',gateway,'gateway_secret',secret,'classroom_id',p_classroom_id);
end $function$
;

CREATE OR REPLACE FUNCTION public.aire_enroll_pc(p_classroom_id uuid, p_origin_id uuid, p_secret text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare g public.aire_gateways;
begin
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula' using errcode='42501'; end if;
 if p_origin_id is null or p_secret is null or length(p_secret) not between 40 and 200 then raise exception 'Identidad de PC inválida'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into g from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc' and origin_id=p_origin_id limit 1;
 if g.id is not null then
  if g.classroom_id is distinct from p_classroom_id or g.secret_hash is distinct from sha256(convert_to(p_secret,'UTF8')) then raise exception 'Esta identidad ya está vinculada. Use su configuración local' using errcode='42501'; end if;
  return jsonb_build_object('classroom_id',g.classroom_id,'gateway_id',g.id);
 end if;
 if (select count(*) from public.aire_gateways where classroom_id=p_classroom_id and enabled and kind='pc')>=aire_private.pc_registration_limit() then raise exception 'CUOTA_RECEPTORES: se alcanzaron las 10 PC habilitadas de esta aula. Retire solo equipos que ya no se utilicen'; end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: límite preventivo de tamaño'; end if;
 insert into public.aire_gateways(classroom_id,name,secret_hash,origin_id) values(p_classroom_id,'PC del aula',sha256(convert_to(p_secret,'UTF8')),p_origin_id) returning * into g;
 return jsonb_build_object('classroom_id',g.classroom_id,'gateway_id',g.id);
end $function$
;

commit;
