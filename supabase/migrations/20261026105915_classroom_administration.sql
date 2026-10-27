-- Administración por aula; correos visibles solo a administradores de esa aula.
begin;
alter table public.aire_classrooms add column revision integer not null default 1;
create function public.aire_classroom_admin(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores de esta aula' using errcode='42501'; end if;
 return public.aire_meter_response(jsonb_build_object(
 'classroom',(select jsonb_build_object('id',id,'name',name,'school',school,'revision',revision) from public.aire_classrooms where id=p_classroom_id),
 'can_edit',true,'can_manage_members',true,
 'members',coalesce((select jsonb_agg(jsonb_build_object('id',m.user_id,'email',u.email,'role',m.role,
 'owner',m.user_id=c.owner_id,'current',m.user_id=auth.uid(),
 'phone_count',(select count(*) from public.aire_phones p where p.classroom_id=m.classroom_id and p.user_id=m.user_id),
 'last_registered_at',(select max(updated_at) from public.aire_phones p where p.classroom_id=m.classroom_id and p.user_id=m.user_id),
 'last_received_at',(select max(received_at) from public.aire_deliveries d where d.classroom_id=m.classroom_id and d.user_id=m.user_id)) order by lower(u.email))
 from public.aire_members m join auth.users u on u.id=m.user_id join public.aire_classrooms c on c.id=m.classroom_id where m.classroom_id=p_classroom_id),'[]'::jsonb),
 'member_limit',10,'account_creation_available',(select count(*)<50 from auth.users)));
end $$;
create function public.aire_update_classroom(p_classroom_id uuid,p_revision integer,p_name text,p_school text) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform pg_advisory_xact_lock(173034001);
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores de esta aula' using errcode='42501'; end if;
 if p_name is null or length(trim(p_name)) not between 2 and 100 or p_school is null or length(trim(p_school))>120 then raise exception 'Revise nombre e institución'; end if;
 update public.aire_classrooms set name=trim(p_name),school=trim(p_school),revision=revision+1 where id=p_classroom_id and revision=p_revision;
 if not found then raise exception 'El aula cambió. Actualice antes de editar' using errcode='40001'; end if;
end $$;
create or replace function public.aire_grant_member(p_classroom_id uuid,p_email text,p_role text) returns void
language plpgsql security definer set search_path='' as $$
declare target uuid;
begin
 perform pg_advisory_xact_lock(173034001);
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores de esta aula' using errcode='42501'; end if;
 if p_email is null or length(trim(p_email))>254 or p_role is null or p_role not in ('admin','docente','observador') then raise exception 'Revise correo y rol'; end if;
 select id into target from auth.users where lower(email)=lower(trim(p_email));
 if target is null then raise exception 'ACCOUNT_NOT_FOUND'; end if;
 if exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=target) and p_role<>'admin' then raise exception 'El propietario debe conservar administración'; end if;
 if target=auth.uid() and p_role<>'admin' then raise exception 'No puede retirar su propia administración'; end if;
 if not exists(select 1 from public.aire_members where classroom_id=p_classroom_id and user_id=target)
 and (select count(*) from public.aire_members where classroom_id=p_classroom_id)>=10 then raise exception 'Se alcanzó el límite preventivo de diez personas del aula'; end if;
 insert into public.aire_members values(p_classroom_id,target,p_role) on conflict(classroom_id,user_id) do update set role=excluded.role;
end $$;
create function public.aire_remove_member(p_classroom_id uuid,p_user_id uuid) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform pg_advisory_xact_lock(173034001);
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores de esta aula' using errcode='42501'; end if;
 if p_user_id is null or p_user_id=auth.uid() or exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=p_user_id) then raise exception 'No puede retirar al propietario ni su propio acceso'; end if;
 update public.aire_deliveries set status='cancelado',lease_id=null,lease_until=null where classroom_id=p_classroom_id and user_id=p_user_id and status in ('pendiente','reintento');
 delete from public.aire_phones where classroom_id=p_classroom_id and user_id=p_user_id;
 delete from public.aire_members where classroom_id=p_classroom_id and user_id=p_user_id;
end $$;
create or replace function public.aire_admin_capabilities(p_classroom_id uuid default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare role_name text; creator boolean; owner boolean; rooms integer; active_count integer;
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 role_name:=public.aire_role(p_classroom_id);
 if p_classroom_id is not null and role_name is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 creator:=exists(select 1 from public.aire_creators where user_id=auth.uid());
 owner:=exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid());
 select count(*) into rooms from public.aire_classrooms;
 select count(*) into active_count from public.aire_gateways where classroom_id=p_classroom_id and enabled;
 return public.aire_meter_response(jsonb_build_object(
  'classroom_id',p_classroom_id,'can_create_classroom',creator and rooms<3,
  'can_manage_members',coalesce(role_name='admin',false),'can_manage_gateways',coalesce(role_name='admin',false),
  'create_reason',case when not creator then 'Esta cuenta no está habilitada para crear aulas' when rooms>=3 then 'Se alcanzó el máximo preventivo de tres aulas' else null end,
  'members_reason',case when role_name is distinct from 'admin' then 'Solo administradores del aula pueden gestionar personas' else null end,
  'gateway_limit',2,'active_gateways',active_count,
  'gateway_total',(select count(*) from public.aire_gateways where classroom_id=p_classroom_id),
  'gateways',case when role_name='admin' then coalesce((select jsonb_agg(jsonb_build_object(
    'id',id,'name',name,'enabled',enabled,'revision',revision,'last_seen_at',last_seen_at,'paired',origin_id is not null,'revoked_at',revoked_at,'revoked_by',revoked_by,'revoked_reason',revoked_reason)
    order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id) from (select * from public.aire_gateways where classroom_id=p_classroom_id order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id limit 50) listed),'[]'::jsonb) else '[]'::jsonb end));
end $$;
revoke all on function public.aire_admin_capabilities(uuid) from public,anon,service_role;
grant execute on function public.aire_admin_capabilities(uuid) to authenticated;
revoke all on function public.aire_classroom_admin(uuid) from public,anon,service_role;
grant execute on function public.aire_classroom_admin(uuid) to authenticated;
revoke all on function public.aire_update_classroom(uuid,integer,text,text) from public,anon,service_role;
grant execute on function public.aire_update_classroom(uuid,integer,text,text) to authenticated;
revoke all on function public.aire_grant_member(uuid,text,text) from public,anon,service_role;
grant execute on function public.aire_grant_member(uuid,text,text) to authenticated;
revoke all on function public.aire_remove_member(uuid,uuid) from public,anon,service_role;
grant execute on function public.aire_remove_member(uuid,uuid) to authenticated;
commit;
