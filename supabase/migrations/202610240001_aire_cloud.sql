-- SFA Aire 0.2. Proyecto Supabase independiente. Aplicar como administrador SQL.
begin;
create table public.aire_classrooms (
 id uuid primary key default gen_random_uuid(), name text not null check(length(name) between 2 and 100),
 school text not null default '' check(length(school)<=120), owner_id uuid not null references auth.users(id),
 created_at timestamptz not null default now());
create table public.aire_members (
 classroom_id uuid references public.aire_classrooms on delete cascade, user_id uuid references auth.users on delete cascade,
 role text not null check(role in ('admin','docente','observador')), primary key(classroom_id,user_id));
create table public.aire_gateways (
 id uuid primary key default gen_random_uuid(), classroom_id uuid not null references public.aire_classrooms,
 name text not null check(length(name) between 2 and 100), secret_hash bytea not null,
 origin_id uuid, last_seq bigint not null default 0, enabled boolean not null default true);
create table public.aire_readings (
 id bigint generated always as identity primary key, classroom_id uuid not null references public.aire_classrooms,
 gateway_id uuid not null references public.aire_gateways, seq bigint not null,
 source text not null check(source in ('arduino','simulacion')), sample_at timestamptz not null,
 ingested_at timestamptz not null default now(), state text not null, observation jsonb not null,
 unique(gateway_id,seq));
create index aire_reading_time on public.aire_readings(classroom_id,sample_at desc);
create table public.aire_snapshots (
 gateway_id uuid references public.aire_gateways, source text check(source in ('arduino','simulacion')),
 classroom_id uuid not null references public.aire_classrooms, sample_at timestamptz not null,
 ingested_at timestamptz not null default now(), state text not null, observation jsonb not null,
 primary key(gateway_id,source));
create table public.aire_incidents (
 id uuid primary key, classroom_id uuid not null references public.aire_classrooms,
 gateway_id uuid not null references public.aire_gateways, source text not null check(source in ('arduino','simulacion')),
 severity text not null check(severity in ('aviso','alerta')), opened_at timestamptz not null,
 updated_at timestamptz not null default now(), status text not null default 'pendiente'
 check(status in ('pendiente','en_atencion','resuelto')), assigned_to uuid references auth.users,
 note text not null default '', revision integer not null default 1, historical boolean not null default false);
create table public.aire_attention_log (
 id bigint generated always as identity primary key, classroom_id uuid not null references public.aire_classrooms,
 incident_id uuid not null references public.aire_incidents, actor uuid not null references auth.users,
 action text not null, note text not null, created_at timestamptz not null default now());
create table public.aire_phones (
 classroom_id uuid references public.aire_classrooms, user_id uuid references auth.users,
 installation_id text not null, token text not null, name text not null,
 accept_simulations boolean not null default false, updated_at timestamptz not null default now(),
 primary key(classroom_id,user_id,installation_id));
create table public.aire_deliveries (
 id uuid primary key default gen_random_uuid(), classroom_id uuid not null references public.aire_classrooms,
 incident_id uuid not null references public.aire_incidents, user_id uuid not null references auth.users,
 installation_id text not null, severity text not null,
 status text not null default 'pendiente', attempts integer not null default 0,
 created_at timestamptz not null default now(), next_try timestamptz not null default now(),
 lease_id uuid, lease_until timestamptz, provider_id text, error text,
 received_at timestamptz, opened_at timestamptz,
 unique(incident_id,user_id,installation_id,severity));

-- Función auxiliar que consulta membresías sin recursión de políticas.
create function public.aire_role(p_classroom_id uuid) returns text
language sql stable security definer set search_path='' as $$
 select role from public.aire_members where classroom_id=p_classroom_id and user_id=auth.uid()
$$;
revoke all on function public.aire_role(uuid) from public;
grant execute on function public.aire_role(uuid) to authenticated;

alter table public.aire_classrooms enable row level security;
alter table public.aire_members enable row level security;
alter table public.aire_gateways enable row level security;
alter table public.aire_readings enable row level security;
alter table public.aire_snapshots enable row level security;
alter table public.aire_incidents enable row level security;
alter table public.aire_attention_log enable row level security;
alter table public.aire_phones enable row level security;
alter table public.aire_deliveries enable row level security;
revoke all on public.aire_classrooms,public.aire_members,public.aire_gateways,public.aire_readings,
 public.aire_snapshots,public.aire_incidents,public.aire_attention_log,public.aire_phones,public.aire_deliveries from anon,authenticated;
grant select on public.aire_classrooms,public.aire_members,public.aire_readings,public.aire_snapshots,
 public.aire_incidents,public.aire_attention_log,public.aire_deliveries to authenticated;
create policy classrooms_read on public.aire_classrooms for select to authenticated using(public.aire_role(id) is not null);
create policy members_read on public.aire_members for select to authenticated using(public.aire_role(classroom_id) is not null);
create policy readings_read on public.aire_readings for select to authenticated using(public.aire_role(classroom_id) is not null);
create policy snapshots_read on public.aire_snapshots for select to authenticated using(public.aire_role(classroom_id) is not null);
create policy incidents_read on public.aire_incidents for select to authenticated using(public.aire_role(classroom_id) is not null);
create policy attention_read on public.aire_attention_log for select to authenticated using(public.aire_role(classroom_id) is not null);
create policy deliveries_read on public.aire_deliveries for select to authenticated using(public.aire_role(classroom_id) is not null);

create function public.aire_create_classroom(p_name text,p_school text default '') returns uuid
language plpgsql security definer set search_path='' as $$
declare room uuid;
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 insert into public.aire_classrooms(name,school,owner_id) values(trim(p_name),trim(p_school),auth.uid()) returning id into room;
 insert into public.aire_members values(room,auth.uid(),'admin'); return room;
end $$;

create function public.aire_grant_member(p_classroom_id uuid,p_email text,p_role text) returns void
language plpgsql security definer set search_path='' as $$
declare member_id uuid;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 if p_role not in ('admin','docente','observador') then raise exception 'Rol inválido'; end if;
 select id into member_id from auth.users where lower(email)=lower(trim(p_email));
 if member_id is null then raise exception 'La cuenta debe existir en Auth antes de asignarla'; end if;
 if exists(select 1 from public.aire_classrooms where id=p_classroom_id and owner_id=member_id) and p_role!='admin' then raise exception 'No se puede degradar al propietario'; end if;
 insert into public.aire_members values(p_classroom_id,member_id,p_role)
 on conflict(classroom_id,user_id) do update set role=excluded.role;
end $$;

create function public.aire_create_gateway(p_classroom_id uuid,p_name text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare secret text; gateway uuid;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 secret:=gen_random_uuid()::text||gen_random_uuid()::text;
 insert into public.aire_gateways(classroom_id,name,secret_hash)
 values(p_classroom_id,trim(p_name),sha256(convert_to(secret,'UTF8'))) returning id into gateway;
 return jsonb_build_object('gateway_id',gateway,'gateway_secret',secret,'classroom_id',p_classroom_id);
end $$;

-- Solo usa el secreto limitado a un receptor. Nunca requiere service_role en PC.
create function public.aire_ingest(p_gateway_id uuid,p_secret text,p_packet jsonb) returns jsonb
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
   if changed and not incident.historical and opened>=now()-interval '60 seconds' then
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

create function public.aire_attention(p_incident_id uuid,p_revision integer,p_action text,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; role_name text;
begin
 select * into item from public.aire_incidents where id=p_incident_id for update;
 role_name:=public.aire_role(item.classroom_id);
 if role_name is null or role_name not in ('admin','docente') then raise exception 'Sin permiso para atender' using errcode='42501'; end if;
 if p_action not in ('atender','resolver') or length(trim(p_note)) not between 3 and 500 then raise exception 'Acción o nota inválida'; end if;
 if item.revision!=p_revision or item.status='resuelto' then raise exception 'El incidente cambió; actualice la vista' using errcode='40001'; end if;
 if item.assigned_to is not null and item.assigned_to!=auth.uid() and role_name!='admin' then raise exception 'Otro responsable está atendiendo el incidente' using errcode='42501'; end if;
 if p_action='resolver' and not exists(select 1 from public.aire_snapshots s where s.gateway_id=item.gateway_id and s.source=item.source and s.state='normal' and s.sample_at between now()-interval '10 seconds' and now()+interval '5 seconds') then
  raise exception 'Se necesitan lecturas normales recientes de la misma fuente';
 end if;
 update public.aire_incidents set status=case when p_action='resolver' then 'resuelto' else 'en_atencion' end,
  assigned_to=auth.uid(),note=trim(p_note),revision=revision+1,updated_at=now() where id=item.id;
 insert into public.aire_attention_log(classroom_id,incident_id,actor,action,note) values(item.classroom_id,item.id,auth.uid(),p_action,trim(p_note));
 if p_action='resolver' then update public.aire_deliveries set status='cancelado' where incident_id=item.id and status in ('pendiente','reintento'); end if;
end $$;

create function public.aire_register_phone(p_classroom_id uuid,p_installation_id text,p_token text,p_name text,p_accept_simulations boolean default false) returns void
language plpgsql security definer set search_path='' as $$
begin
 if public.aire_role(p_classroom_id) is null then raise exception 'Sin acceso al aula' using errcode='42501'; end if;
 if length(p_token) not between 20 and 4096 or length(p_installation_id) not between 8 and 120 or length(p_name)>100 then raise exception 'Dispositivo inválido'; end if;
 insert into public.aire_phones values(p_classroom_id,auth.uid(),p_installation_id,p_token,p_name,p_accept_simulations,now())
 on conflict(classroom_id,user_id,installation_id) do update set token=excluded.token,name=excluded.name,accept_simulations=excluded.accept_simulations,updated_at=now();
end $$;

create function public.aire_receipt(p_delivery_id uuid,p_installation_id text,p_action text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if p_action not in ('recibido','abierto') then raise exception 'Acuse inválido'; end if;
 update public.aire_deliveries set received_at=coalesce(received_at,now()),
  opened_at=case when p_action='abierto' then coalesce(opened_at,now()) else opened_at end,status='recibido_app'
 where id=p_delivery_id and user_id=auth.uid() and installation_id=p_installation_id and public.aire_role(classroom_id) is not null;
 if not found then raise exception 'Entrega no autorizada' using errcode='42501'; end if;
end $$;

create function public.aire_unregister_phone(p_installation_id text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 delete from public.aire_phones where user_id=auth.uid() and installation_id=p_installation_id;
 update public.aire_deliveries set status='cancelado' where user_id=auth.uid() and installation_id=p_installation_id and status in ('pendiente','reintento');
end $$;

create function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways; result jsonb;
begin
 select * into g from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8'));
 if not found then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 update public.aire_deliveries d set status='vencido' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and d.created_at<now()-interval '5 minutes';
 update public.aire_deliveries d set status='cancelado' from public.aire_incidents i where d.incident_id=i.id and i.gateway_id=g.id
  and d.status in ('pendiente','reintento') and (i.status='resuelto' or not exists(select 1 from public.aire_members m where m.classroom_id=d.classroom_id and m.user_id=d.user_id));
 with jobs as (
  select d.id from public.aire_deliveries d join public.aire_incidents i on i.id=d.incident_id
  where i.gateway_id=g.id and d.status in ('pendiente','reintento') and d.next_try<=now()
   and (d.lease_until is null or d.lease_until<now()) and d.attempts<5
  order by d.created_at limit 20 for update of d skip locked
 ), claimed as (
  update public.aire_deliveries d set lease_id=gen_random_uuid(),lease_until=now()+interval '60 seconds',attempts=attempts+1
  where id in (select id from jobs) returning d.*
 ) select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'lease_id',d.lease_id,'incident_id',d.incident_id,'severity',d.severity,'source',i.source,'token',p.token)),'[]'::jsonb) into result
 from claimed d join public.aire_incidents i on i.id=d.incident_id join public.aire_phones p
 on p.classroom_id=d.classroom_id and p.user_id=d.user_id and p.installation_id=d.installation_id;
 return jsonb_build_object('jobs',result);
end $$;

create function public.aire_finish_push(p_gateway_id uuid,p_secret text,p_delivery_id uuid,p_lease_id uuid,p_provider_id text default null,p_error text default null) returns void
language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8'))) then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 update public.aire_deliveries d set
  status=case when received_at is not null then 'recibido_app' when status='cancelado' then 'cancelado' when p_error is null then 'aceptado_fcm' when attempts>=5 or p_error in ('UnregisteredError','SenderIdMismatchError') then 'error' else 'reintento' end,
  provider_id=left(p_provider_id,250),error=left(p_error,100),next_try=now()+make_interval(secs=>least(300,power(2,attempts)::integer*5)),lease_id=null,lease_until=null
 where d.id=p_delivery_id and d.lease_id=p_lease_id and exists(select 1 from public.aire_incidents i where i.id=d.incident_id and i.gateway_id=p_gateway_id);
 if not found then raise exception 'Lease de entrega inválido'; end if;
end $$;

create function public.aire_overview() returns jsonb language sql stable security invoker set search_path='' as $$
 select jsonb_build_object(
 'classrooms',coalesce((select jsonb_agg(to_jsonb(c)) from public.aire_classrooms c),'[]'::jsonb),
 'memberships',coalesce((select jsonb_agg(to_jsonb(m)) from public.aire_members m where m.user_id=auth.uid()),'[]'::jsonb),
 'snapshots',coalesce((select jsonb_agg(to_jsonb(s)) from public.aire_snapshots s),'[]'::jsonb),
 'incidents',coalesce((select jsonb_agg(to_jsonb(i)) from (select * from public.aire_incidents order by opened_at desc limit 100) i),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from (select id,classroom_id,incident_id,status,attempts,error,received_at,opened_at from public.aire_deliveries order by created_at desc limit 100) d),'[]'::jsonb))
$$;

create function public.aire_gateway_status(p_gateway_id uuid,p_secret text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways;
begin
 select * into g from public.aire_gateways where id=p_gateway_id and enabled and secret_hash=sha256(convert_to(p_secret,'UTF8'));
 if not found then raise exception 'Receptor no autorizado' using errcode='42501'; end if;
 return jsonb_build_object('classroom_id',g.classroom_id,'incidents',coalesce((select jsonb_agg(to_jsonb(i)) from (
  select id,status,note,severity from public.aire_incidents where gateway_id=g.id order by updated_at desc limit 100) i),'[]'::jsonb));
end $$;

create function public.aire_history(p_classroom_id uuid,p_source text) returns jsonb language sql stable security invoker set search_path='' as $$
 select jsonb_build_object('readings',coalesce((select jsonb_agg(to_jsonb(r)) from
  (select * from public.aire_readings where classroom_id=p_classroom_id and source=p_source order by sample_at desc limit 200) r),'[]'::jsonb))
$$;

-- Cierre explícito: las funciones SECURITY DEFINER no son públicas por defecto.
revoke all on function public.aire_create_classroom(text,text),public.aire_grant_member(uuid,text,text),
 public.aire_create_gateway(uuid,text),public.aire_attention(uuid,integer,text,text),
 public.aire_register_phone(uuid,text,text,text,boolean),public.aire_receipt(uuid,text,text),
 public.aire_overview(),public.aire_history(uuid,text),public.aire_unregister_phone(text) from public;
grant execute on function public.aire_create_classroom(text,text),public.aire_grant_member(uuid,text,text),
 public.aire_create_gateway(uuid,text),public.aire_attention(uuid,integer,text,text),
 public.aire_register_phone(uuid,text,text,text,boolean),public.aire_receipt(uuid,text,text),
 public.aire_overview(),public.aire_history(uuid,text),public.aire_unregister_phone(text) to authenticated;
revoke all on function public.aire_ingest(uuid,text,jsonb),public.aire_claim_push(uuid,text),
 public.aire_finish_push(uuid,text,uuid,uuid,text,text),public.aire_gateway_status(uuid,text) from public;
grant execute on function public.aire_ingest(uuid,text,jsonb),public.aire_claim_push(uuid,text),
 public.aire_finish_push(uuid,text,uuid,uuid,text,text),public.aire_gateway_status(uuid,text) to anon,authenticated;
commit;
