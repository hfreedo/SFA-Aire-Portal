-- Invitaciones de un solo uso. Los secretos no se guardan en texto ni en listados.
begin;
create table aire_private.invitations (
 id uuid primary key default gen_random_uuid(), classroom_id uuid not null references public.aire_classrooms,
 email text not null, role text not null check(role in ('admin','docente','observador')), activation boolean not null,
 token_hash text not null unique check(token_hash ~ '^[0-9a-f]{64}$'),
 created_by uuid not null references auth.users, created_at timestamptz not null default now(),
 expires_at timestamptz not null default now()+interval '1 hour',
 revoked_at timestamptz, accepted_at timestamptz, accepted_by uuid references auth.users);
alter table aire_private.invitations enable row level security;
revoke all on aire_private.invitations from public,anon,authenticated,service_role;
create index aire_invitation_room on aire_private.invitations(classroom_id,created_at desc);

create function public.aire_invite_create(p_classroom_id uuid,p_email text,p_role text,p_hash text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare item aire_private.invitations; needs_activation boolean;
begin
 perform pg_advisory_xact_lock(173034001);
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula' using errcode='42501'; end if;
 if p_email is null or length(trim(p_email))>254 or trim(p_email)!~'^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' or p_role is null or p_role not in ('admin','docente','observador') or p_hash is null or p_hash!~'^[0-9a-f]{64}$' then raise exception 'Revise correo y permiso'; end if;
 p_email:=lower(trim(p_email));
 if exists(select 1 from public.aire_members m join auth.users u on u.id=m.user_id where m.classroom_id=p_classroom_id and lower(u.email)=p_email) then raise exception 'Esta persona ya tiene acceso. Use Editar acceso'; end if;
 if exists(select 1 from aire_private.invitations where classroom_id=p_classroom_id and email=p_email and revoked_at is null and accepted_at is null and expires_at>now()) then raise exception 'Ya hay una invitación vigente. Revóquela antes de generar otra'; end if;
 if (select count(*) from aire_private.invitations where created_at>now()-interval '24 hours')>=10 then raise exception 'Límite preventivo de diez invitaciones por día'; end if;
 if (select count(*) from public.aire_members where classroom_id=p_classroom_id)+(select count(*) from aire_private.invitations where classroom_id=p_classroom_id and revoked_at is null and accepted_at is null and expires_at>now())>=10 then raise exception 'Las personas e invitaciones vigentes ocupan los diez lugares del aula'; end if;
 select not exists(select 1 from auth.users where lower(email)=p_email) or exists(select 1 from auth.users u where lower(email)=p_email and to_jsonb(u)->>'invited_at' is not null and to_jsonb(u)->>'email_confirmed_at' is null) into needs_activation;
 if needs_activation and (select count(*) from auth.users)+(select count(*) from aire_private.invitations i where i.activation and revoked_at is null and accepted_at is null and expires_at>now())>=50 then raise exception 'Límite preventivo de cuentas alcanzado'; end if;
 delete from aire_private.invitations where created_at<now()-interval '30 days';
 insert into aire_private.invitations(classroom_id,email,role,token_hash,created_by,activation) values(p_classroom_id,p_email,p_role,p_hash,auth.uid(),needs_activation) returning * into item;
 return jsonb_build_object('id',item.id,'email',item.email,'expires_at',item.expires_at,'activation',needs_activation);
end $$;

create function public.aire_invite_list(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores del aula' using errcode='42501'; end if;
 return public.aire_meter_response(coalesce((select jsonb_agg(jsonb_build_object('id',id,'email',email,'role',role,'expires_at',expires_at,'status',case when accepted_at is not null then 'aceptada' when revoked_at is not null then 'revocada' when expires_at<=now() then 'vencida' else 'pendiente' end) order by created_at desc) from (select * from aire_private.invitations where classroom_id=p_classroom_id order by created_at desc limit 30) i),'[]'::jsonb));
end $$;

create function public.aire_invite_revoke(p_id uuid) returns void
language plpgsql security definer set search_path='' as $$
declare room uuid;
begin
 perform pg_advisory_xact_lock(173034001);
 select classroom_id into room from aire_private.invitations where id=p_id;
 if auth.uid() is null or public.aire_role(room) is distinct from 'admin' then raise exception 'Solo administradores del aula' using errcode='42501'; end if;
 update aire_private.invitations set revoked_at=coalesce(revoked_at,now()) where id=p_id and accepted_at is null;
end $$;

create function public.aire_invite_accept(p_token text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare item aire_private.invitations; who uuid:=auth.uid(); address text;
begin
 perform pg_advisory_xact_lock(173034001);
 if who is null then raise exception 'Inicie sesión para aceptar' using errcode='42501'; end if;
 if p_token is null or p_token!~'^[0-9a-f]{64}$' then raise exception 'Invitación inválida'; end if;
 select * into item from aire_private.invitations where token_hash=encode(sha256(convert_to(p_token,'UTF8')),'hex') for update;
 select lower(email) into address from auth.users where id=who;
 if item.id is null or address is distinct from item.email then raise exception 'La invitación no corresponde a esta cuenta' using errcode='42501'; end if;
 if item.accepted_by=who and item.accepted_at is not null then return jsonb_build_object('classroom_id',item.classroom_id,'accepted',true); end if;
 if item.revoked_at is not null or item.expires_at<=now() or item.accepted_at is not null or not exists(select 1 from public.aire_members where classroom_id=item.classroom_id and user_id=item.created_by and role='admin') then raise exception 'La invitación venció o fue revocada. Solicite una nueva'; end if;
 if exists(select 1 from public.aire_members where classroom_id=item.classroom_id and user_id=who) then raise exception 'Ya tiene acceso al aula. Solicite al administrador revisar su permiso'; end if;
 if (select count(*) from public.aire_members where classroom_id=item.classroom_id)>=10 then raise exception 'Límite preventivo de personas del aula'; end if;
 insert into public.aire_members(classroom_id,user_id,role) values(item.classroom_id,who,item.role);
 update aire_private.invitations set accepted_at=now(),accepted_by=who where id=item.id;
 return jsonb_build_object('classroom_id',item.classroom_id,'accepted',true);
end $$;
revoke all on function public.aire_invite_create(uuid,text,text,text),public.aire_invite_list(uuid),public.aire_invite_revoke(uuid),public.aire_invite_accept(text) from public,anon,authenticated,service_role;
grant execute on function public.aire_invite_create(uuid,text,text,text),public.aire_invite_list(uuid),public.aire_invite_revoke(uuid),public.aire_invite_accept(text) to authenticated;
commit;
