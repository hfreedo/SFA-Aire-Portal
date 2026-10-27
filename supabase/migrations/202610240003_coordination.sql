-- SFA Aire 0.4. Aplicar después de 001 y 002. Sin servicios adicionales.
begin;
-- Registro de habilitación, administrado exclusivamente desde SQL de confianza.
-- Los propietarios existentes conservan la capacidad de crear aulas.
create table public.aire_creators(user_id uuid primary key references auth.users);
insert into public.aire_creators select distinct owner_id from public.aire_classrooms;
create table public.aire_duty(
 classroom_id uuid primary key references public.aire_classrooms,
 coordinator uuid not null references auth.users, teacher uuid not null references auth.users,
 deputy uuid references auth.users, revision integer not null default 1,
 updated_at timestamptz not null default now(),
 check(coordinator<>teacher and (deputy is null or (deputy<>coordinator and deputy<>teacher))));
alter table public.aire_incidents add column coordinator_id uuid references auth.users;
create table public.aire_instructions(
 id uuid primary key, incident_id uuid not null references public.aire_incidents,
 recipient uuid not null references auth.users, author uuid not null references auth.users,
 version integer not null, action text not null check(length(action) between 3 and 500),
 reason text not null check(length(reason) between 3 and 500), validity_minutes integer not null check(validity_minutes between 1 and 120), expires_at timestamptz not null,
 status text not null default 'emitida' check(status in ('emitida','confirmada','aclaracion','impedimento','realizada','parcial','reemplazada')),
 response text not null default '', revision integer not null default 1,
 created_at timestamptz not null default now(), unique(incident_id,version));
create unique index aire_one_instruction on public.aire_instructions(incident_id) where status<>'reemplazada';
create table public.aire_coord_events(
 id uuid primary key default gen_random_uuid(), incident_id uuid not null references public.aire_incidents,
 instruction_id uuid references public.aire_instructions, actor uuid not null references auth.users,
 kind text not null, notification_state text not null default 'sin_destinatario', note text not null check(length(note)<=1000), created_at timestamptz not null default now());
create index aire_coord_timeline on public.aire_coord_events(incident_id,created_at desc);
alter table public.aire_deliveries add column event_id uuid references public.aire_coord_events;
-- Conservar la clave del contrato v0.2: cada evento usa coord:UUID como clave interna.
create unique index aire_delivery_event_unique on public.aire_deliveries(event_id,user_id,installation_id) where event_id is not null;
alter table public.aire_creators enable row level security;
alter table public.aire_duty enable row level security;
alter table public.aire_instructions enable row level security;
alter table public.aire_coord_events enable row level security;
revoke all on public.aire_creators,public.aire_duty,public.aire_instructions,public.aire_coord_events from public,anon,authenticated;

create or replace function public.aire_create_classroom(p_name text,p_school text default '') returns uuid
language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from public.aire_creators where user_id=auth.uid()) then raise exception 'Creación reservada al responsable institucional habilitado' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(173034001);
 if (select count(*) from public.aire_classrooms)>=3 then raise exception 'CUOTA_AULAS: máximo preventivo de 3 aulas'; end if;
 return public.aire_create_classroom_v02(p_name,p_school);
end $$;
create or replace function public.aire_grant_member(p_classroom_id uuid,p_email text,p_role text) returns void
language plpgsql security definer set search_path='' as $$
declare target uuid;
begin
 if not exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid()) then raise exception 'Solo responsable institucional del aula' using errcode='42501'; end if;
 if p_role is null or p_role not in ('admin','docente','observador') then raise exception 'Rol inválido'; end if;
 select id into target from auth.users where lower(email)=lower(trim(p_email));
 if target is null then raise exception 'Primero cree la cuenta en Auth'; end if;
 if exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=target) and p_role<>'admin' then raise exception 'No degradar al propietario'; end if;
 if not exists(select 1 from public.aire_members where classroom_id=p_classroom_id and user_id=target) and (select count(*) from public.aire_members where classroom_id=p_classroom_id)>=10 then raise exception 'CUOTA_PERSONAS: máximo preventivo de 10 cuentas por aula'; end if;
 if p_role='observador' and exists(select 1 from public.aire_duty where classroom_id=p_classroom_id and target in (coordinator,teacher,deputy)) then raise exception 'Reasigne primero su responsabilidad operativa'; end if;
 insert into public.aire_members values(p_classroom_id,target,p_role) on conflict(classroom_id,user_id) do update set role=excluded.role;
end $$;

create function public.aire_set_duty(p_classroom_id uuid,p_revision integer,p_coordinator uuid,p_teacher uuid,p_deputy uuid default null) returns void
language plpgsql security definer set search_path='' as $$
declare current_revision integer;
begin
 perform pg_advisory_xact_lock(173034001);
 perform 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid() for update;
 if not found then raise exception 'Solo responsable institucional del aula' using errcode='42501'; end if;
 select revision into current_revision from public.aire_duty where classroom_id=p_classroom_id for update;
 if coalesce(current_revision,0) is distinct from p_revision then raise exception 'La asignación cambió; actualice' using errcode='40001'; end if;
 if p_coordinator is null or p_teacher is null or exists(select 1 from unnest(array[p_coordinator,p_teacher,p_deputy]) u where u is not null and not exists(select 1 from public.aire_members m where m.classroom_id=p_classroom_id and m.user_id=u and m.role in ('docente','admin'))) then raise exception 'Asigne cuentas con acceso operativo al aula'; end if;
 if exists(select 1 from public.aire_incidents where classroom_id=p_classroom_id and status<>'resuelto' and coordinator_id is not null) then raise exception 'Cierre o transfiera los incidentes antes de cambiar el turno'; end if;
 insert into public.aire_duty values(p_classroom_id,p_coordinator,p_teacher,p_deputy,1,now())
 on conflict(classroom_id) do update set coordinator=excluded.coordinator,teacher=excluded.teacher,deputy=excluded.deputy,revision=public.aire_duty.revision+1,updated_at=now();
end $$;

-- Interna: evento y notificación se confirman en la misma transacción. Las acciones
-- quedan registradas incluso si no hay teléfono o se agotó el cupo de push.
create function public.aire_coord_event(p_incident uuid,p_instruction uuid,p_kind text,p_note text,p_target uuid) returns uuid
language plpgsql security definer set search_path='' as $$
declare eid uuid; item public.aire_incidents; n integer;
begin
 perform pg_advisory_xact_lock(173034001);
 if pg_database_size(current_database())>=314572800 or (select count(*) from public.aire_coord_events)>=20000 then raise exception 'CUOTA_COORDINACION: archivar historial antes de continuar'; end if;
 select * into item from public.aire_incidents where id=p_incident;
 insert into public.aire_coord_events(incident_id,instruction_id,actor,kind,note) values(p_incident,p_instruction,auth.uid(),p_kind,p_note) returning id into eid;
 insert into public.aire_free_usage(day) values(current_date) on conflict do nothing;
 if (select push_jobs from public.aire_free_usage where day=current_date)<97
 and (item.source<>'simulacion' or exists(select 1 from public.aire_lab_runs where id=item.lab_run_id and allow_push and status not in ('cancelado','error'))) then
  insert into public.aire_deliveries(classroom_id,incident_id,user_id,installation_id,severity,event_id)
   select item.classroom_id,item.id,p.user_id,p.installation_id,'coord:'||eid::text,eid from public.aire_phones p
   join public.aire_members m on m.classroom_id=p.classroom_id and m.user_id=p.user_id
   where p.classroom_id=item.classroom_id and p.user_id=p_target and (item.source<>'simulacion' or p.accept_simulations)
   order by p.updated_at desc limit 3;
  get diagnostics n=row_count;
  update public.aire_coord_events set notification_state=case when n>0 then 'encolado' else 'sin_telefono_habilitado' end where id=eid;
  update public.aire_free_usage set push_jobs=push_jobs+n where day=current_date;
 else
  update public.aire_coord_events set notification_state=case when p_target is null then 'sin_destinatario' when (select push_jobs from public.aire_free_usage where day=current_date)>=97 then 'cupo_push_agotado' else 'simulacion_sin_push_autorizado' end where id=eid;
 end if;
 return eid;
end $$;
revoke all on function public.aire_coord_event(uuid,uuid,text,text,uuid) from public,anon,authenticated;

create function public.aire_take_coordination(p_incident_id uuid,p_revision integer,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; duty public.aire_duty;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=p_incident_id for update;
 select * into duty from public.aire_duty where classroom_id=item.classroom_id;
 if public.aire_role(item.classroom_id) is null or auth.uid() is null or (auth.uid() is distinct from duty.coordinator and auth.uid() is distinct from duty.deputy) then raise exception 'Solo coordinación o suplente asignado' using errcode='42501'; end if;
 if item.revision is distinct from p_revision or item.status='resuelto' then raise exception 'Incidente cambiado; actualice' using errcode='40001'; end if;
 if p_note is null or length(trim(p_note)) not between 3 and 500 then raise exception 'Indique motivo del inicio o traspaso'; end if;
 update public.aire_incidents set coordinator_id=auth.uid(),revision=revision+1,updated_at=now() where id=item.id;
 perform public.aire_coord_event(item.id,null,'coordinacion',trim(p_note),duty.teacher);
end $$;

create function public.aire_issue_instruction(p_incident_id uuid,p_revision integer,p_id uuid,p_action text,p_reason text,p_minutes integer) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; duty public.aire_duty; v integer;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=p_incident_id for update;
 select * into duty from public.aire_duty where classroom_id=item.classroom_id;
 if auth.uid() is null or item.coordinator_id is distinct from auth.uid() or public.aire_role(item.classroom_id) is null or (auth.uid() is distinct from duty.coordinator and auth.uid() is distinct from duty.deputy) then raise exception 'Solo coordinador vigente' using errcode='42501'; end if;
 -- UUID estable permite reintentar sin duplicar indicaciones ni push.
 if exists(select 1 from public.aire_instructions where id=p_id and incident_id=item.id and author=auth.uid() and action=trim(p_action) and reason=trim(p_reason) and validity_minutes=p_minutes) then return; end if;
 if item.revision is distinct from p_revision or item.status='resuelto' then raise exception 'Incidente cambiado; actualice' using errcode='40001'; end if;
 if p_action is null or p_reason is null or length(trim(p_action)) not between 3 and 500 or length(trim(p_reason)) not between 3 and 500 or p_minutes is null or p_minutes not between 1 and 120 then raise exception 'Acción, motivo y vigencia de 1 a 120 minutos requeridos'; end if;
 select coalesce(max(version),0)+1 into v from public.aire_instructions where incident_id=item.id;
 update public.aire_instructions set status='reemplazada',revision=revision+1 where incident_id=item.id and status<>'reemplazada';
 update public.aire_deliveries set status='cancelado' where incident_id=item.id and event_id is not null and status in ('pendiente','reintento');
 insert into public.aire_instructions(id,incident_id,recipient,author,version,action,reason,validity_minutes,expires_at) values(p_id,item.id,duty.teacher,auth.uid(),v,trim(p_action),trim(p_reason),p_minutes,now()+make_interval(mins=>p_minutes));
 update public.aire_incidents set revision=revision+1,updated_at=now() where id=item.id;
 perform public.aire_coord_event(item.id,p_id,'indicacion','Nueva indicación versión '||v,duty.teacher);
end $$;

create function public.aire_respond_instruction(p_id uuid,p_revision integer,p_action text,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare ins public.aire_instructions; item public.aire_incidents;
begin
 perform pg_advisory_xact_lock(173034001);
 -- Orden de bloqueo igual al de emisión para evitar interbloqueo.
 select i.* into item from public.aire_incidents i join public.aire_instructions x on x.incident_id=i.id where x.id=p_id for update of i;
 select * into ins from public.aire_instructions where id=p_id for update;
 if auth.uid() is null or ins.recipient is distinct from auth.uid() or public.aire_role(item.classroom_id) is null then raise exception 'Solo responsable destinatario' using errcode='42501'; end if;
 if ins.revision is distinct from p_revision or ins.status in ('reemplazada','realizada') or item.status='resuelto' then raise exception 'Indicación cambiada; actualice' using errcode='40001'; end if;
 if ins.expires_at<=now() then raise exception 'Vigencia vencida: solicite una nueva indicación por el canal acordado'; end if;
 if p_action is null or p_action not in ('confirmada','aclaracion','impedimento','realizada','parcial') or p_note is null or length(trim(p_note)) not between 3 and 500 then raise exception 'Respuesta y explicación requeridas'; end if;
 if p_action in ('realizada','parcial') and ins.status not in ('confirmada','parcial') then raise exception 'Confirme comprensión antes de registrar el resultado'; end if;
 update public.aire_instructions set status=p_action,response=trim(p_note),revision=revision+1 where id=p_id;
 update public.aire_incidents set revision=revision+1,updated_at=now() where id=item.id;
 perform public.aire_coord_event(item.id,p_id,p_action,trim(p_note),item.coordinator_id);
end $$;

-- El RPC anterior sigue disponible para clientes v0.3, con permisos nuevos.
create or replace function public.aire_attention(p_incident_id uuid,p_revision integer,p_action text,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; duty public.aire_duty;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=p_incident_id for update;
 select * into duty from public.aire_duty where classroom_id=item.classroom_id;
 if auth.uid() is null or public.aire_role(item.classroom_id) is null or (auth.uid() is distinct from duty.teacher and auth.uid() is distinct from item.coordinator_id) then raise exception 'Asigne y confirme responsables operativos' using errcode='42501'; end if;
 if item.revision is distinct from p_revision or item.status='resuelto' then raise exception 'Incidente cambiado; actualice' using errcode='40001'; end if;
 if p_action is null or p_action not in ('atender','resolver') or p_note is null or length(trim(p_note)) not between 3 and 500 then raise exception 'Acción y contexto requeridos'; end if;
 if p_action='resolver' then
  if item.coordinator_id is distinct from auth.uid() then raise exception 'Solo coordinación revisa el cierre' using errcode='42501'; end if;
  if exists(select 1 from public.aire_instructions where incident_id=item.id and status not in ('reemplazada','realizada')) then raise exception 'Falta resultado completo de la indicación vigente'; end if;
  if not exists(select 1 from public.aire_snapshots s where s.gateway_id=item.gateway_id and s.source=item.source and s.state='normal' and s.sample_at between now()-interval '95 seconds' and now()+interval '5 seconds' and (item.lab_run_id is null or s.observation->>'lab_run_id'=item.lab_run_id::text)) then raise exception 'Se necesitan lecturas normales recientes del mismo origen'; end if;
 end if;
 update public.aire_incidents set status=case when p_action='resolver' then 'resuelto' else 'en_atencion' end,assigned_to=coalesce(assigned_to,auth.uid()),note=trim(p_note),revision=revision+1,updated_at=now() where id=item.id;
 insert into public.aire_attention_log(classroom_id,incident_id,actor,action,note) values(item.classroom_id,item.id,auth.uid(),p_action,trim(p_note));
 perform public.aire_coord_event(item.id,null,p_action,trim(p_note),case when auth.uid()=duty.teacher then coalesce(item.coordinator_id,duty.coordinator) else duty.teacher end);
 if p_action='resolver' then update public.aire_deliveries set status='cancelado' where incident_id=item.id and status in ('pendiente','reintento'); end if;
end $$;

create function public.aire_coord_panel(p_classroom_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare owner boolean;
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 owner:=exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=auth.uid());
 return public.aire_meter_response(jsonb_build_object('user_id',auth.uid(),'can_manage',owner,'duty',(select to_jsonb(d) from public.aire_duty d where classroom_id=p_classroom_id),
 'people',coalesce((select jsonb_agg(jsonb_build_object('id',m.user_id,'label',case when owner or m.user_id=auth.uid() or exists(select 1 from public.aire_duty t where t.classroom_id=p_classroom_id and m.user_id in (t.coordinator,t.teacher,t.deputy)) then u.email else 'Cuenta '||left(m.user_id::text,8) end,'role',m.role)) from public.aire_members m join auth.users u on u.id=m.user_id where m.classroom_id=p_classroom_id),'[]'::jsonb),
 'instructions',coalesce((select jsonb_agg(to_jsonb(x)) from(select x.* from public.aire_instructions x join public.aire_incidents i on i.id=x.incident_id where i.classroom_id=p_classroom_id and i.id in (select id from public.aire_incidents where classroom_id=p_classroom_id order by opened_at desc limit 30) order by (x.status='reemplazada'),x.created_at desc limit 40)x),'[]'::jsonb),
 'events',coalesce((select jsonb_agg(to_jsonb(e)) from(select e.* from public.aire_coord_events e join public.aire_incidents i on i.id=e.incident_id where i.classroom_id=p_classroom_id order by e.created_at desc limit 60)e),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select d.id,d.incident_id,d.event_id,d.status,d.provider_id,d.received_at,d.opened_at from public.aire_deliveries d where d.classroom_id=p_classroom_id and d.event_id is not null order by d.created_at desc limit 40)d),'[]'::jsonb)));
end $$;

alter function public.aire_claim_push(uuid,text) rename to aire_claim_push_v03;
revoke all on function public.aire_claim_push_v03(uuid,text) from public,anon,authenticated;
create function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 perform public.aire_gateway_status_v02(p_gateway_id,p_secret);
 -- Cancelar entregas pendientes ante reemplazo, vencimiento o revocación.
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i,public.aire_coord_events e
 where d.incident_id=i.id and i.gateway_id=p_gateway_id and d.event_id=e.id and d.status in ('pendiente','reintento')
 and (not exists(select 1 from public.aire_duty t where t.classroom_id=i.classroom_id and d.user_id in (t.coordinator,t.teacher,t.deputy))
 or (e.instruction_id is not null and exists(select 1 from public.aire_instructions x where x.id=e.instruction_id and (x.status='reemplazada' or x.expires_at<=now()))));
 result:=public.aire_claim_push_v03(p_gateway_id,p_secret);
 return jsonb_build_object('jobs',coalesce((select jsonb_agg(j.value||jsonb_build_object('severity',i.severity,'event_id',d.event_id,'event_kind',e.kind)) from jsonb_array_elements(result->'jobs') j join public.aire_deliveries d on d.id=(j.value->>'id')::uuid join public.aire_incidents i on i.id=d.incident_id left join public.aire_coord_events e on e.id=d.event_id),'[]'::jsonb));
end $$;
revoke all on function public.aire_set_duty(uuid,integer,uuid,uuid,uuid),public.aire_take_coordination(uuid,integer,text),public.aire_issue_instruction(uuid,integer,uuid,text,text,integer),public.aire_respond_instruction(uuid,integer,text,text),public.aire_coord_panel(uuid) from public,anon,authenticated;
grant execute on function public.aire_set_duty(uuid,integer,uuid,uuid,uuid),public.aire_take_coordination(uuid,integer,text),public.aire_issue_instruction(uuid,integer,uuid,text,text,integer),public.aire_respond_instruction(uuid,integer,text,text),public.aire_coord_panel(uuid) to authenticated;
revoke all on function public.aire_claim_push(uuid,text) from public;
grant execute on function public.aire_claim_push(uuid,text) to anon,authenticated;
commit;
