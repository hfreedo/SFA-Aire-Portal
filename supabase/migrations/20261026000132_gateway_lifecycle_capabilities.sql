-- Base de ciclo de vida verificada localmente. Despliegue coordinado pendiente.
-- La política de atención vigente se simplifica en 20261026091353; aplicar también esa migración.
-- Gestión de receptores y capacidades de presentación; autorización en cada RPC.
begin;
alter table public.aire_gateways add column revision integer not null default 1;
alter table public.aire_gateways add column revoked_at timestamptz;
alter table public.aire_gateways add column revoked_by uuid references auth.users;
alter table public.aire_gateways add column revoked_reason text;
alter table public.aire_incidents add column closure_kind text check(closure_kind in ('administrativo','normalizacion'));
alter table public.aire_incidents add column closed_by uuid references auth.users;
alter table public.aire_incidents add column closed_at timestamptz;
alter table public.aire_incidents add column closure_reason text;

create or replace function public.aire_create_gateway(p_classroom_id uuid,p_name text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare secret text; gateway uuid;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administrador' using errcode='42501'; end if;
 if p_name is null or length(trim(p_name)) not between 2 and 100 then raise exception 'Nombre de receptor inválido'; end if;
 perform pg_advisory_xact_lock(173034001);
 if (select count(*) from public.aire_gateways where classroom_id=p_classroom_id and enabled)>=2 then
  raise exception 'CUOTA_RECEPTORES: máximo de dos receptores activos por aula. Revoque el anterior para sustituirlo';
 end if;
 if pg_database_size(current_database())>=314572800 then raise exception 'CUOTA_BASE: se alcanzó la guarda preventiva de tamaño'; end if;
 secret:=gen_random_uuid()::text||gen_random_uuid()::text;
 insert into public.aire_gateways(classroom_id,name,secret_hash)
 values(p_classroom_id,trim(p_name),sha256(convert_to(secret,'UTF8'))) returning id into gateway;
 return jsonb_build_object('gateway_id',gateway,'gateway_secret',secret,'classroom_id',p_classroom_id);
end $$;
revoke all on function public.aire_create_gateway(uuid,text) from public,anon,service_role;
grant execute on function public.aire_create_gateway(uuid,text) to authenticated;

create function public.aire_revoke_gateway(p_gateway_id uuid,p_revision integer,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g public.aire_gateways;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into g from public.aire_gateways where id=p_gateway_id for update;
 if g.id is null or public.aire_role(g.classroom_id) is distinct from 'admin' then
  raise exception 'Receptor no autorizado' using errcode='42501';
 end if;
 if p_reason is null or length(trim(p_reason)) not between 3 and 500 then raise exception 'Indique el motivo del retiro'; end if;
 if not g.enabled and p_revision in (g.revision,g.revision-1) then
  return jsonb_build_object('id',g.id,'enabled',false,'revision',g.revision);
 end if;
 if p_revision is distinct from g.revision then raise exception 'El receptor cambió; actualice antes de revocar' using errcode='40001'; end if;
 update public.aire_gateways set enabled=false,push_configured=false,revision=revision+1,revoked_at=now(),revoked_by=auth.uid(),revoked_reason=trim(p_reason) where id=g.id;
 update public.aire_lab_runs set status='cancelado',message='Acceso del receptor revocado',updated_at=now()
 where gateway_id=g.id and status in ('pendiente','ejecutando');
 update public.aire_deliveries d set status='cancelado',lease_id=null,lease_until=null
 where status in ('pendiente','reintento') and exists(select 1 from public.aire_incidents i where i.id=d.incident_id and i.gateway_id=g.id);
 -- Retirar caché de observación actual; historial e incidentes conservan su trazabilidad.
 delete from public.aire_snapshots where gateway_id=g.id;
 return jsonb_build_object('id',g.id,'enabled',false,'revision',g.revision+1);
end $$;
revoke all on function public.aire_revoke_gateway(uuid,integer,text) from public,anon,service_role;
grant execute on function public.aire_revoke_gateway(uuid,integer,text) to authenticated;

create function public.aire_admin_capabilities(p_classroom_id uuid default null) returns jsonb
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
  'can_manage_members',owner,'can_manage_gateways',coalesce(role_name='admin',false),
  'create_reason',case when not creator then 'Esta cuenta no está habilitada para crear aulas' when rooms>=3 then 'Se alcanzó el máximo preventivo de tres aulas' else null end,
  'members_reason',case when not owner then 'Solo el propietario institucional puede asignar cuentas' else null end,
  'gateway_limit',2,'active_gateways',active_count,
  'gateway_total',(select count(*) from public.aire_gateways where classroom_id=p_classroom_id),
  'gateways',case when role_name='admin' then coalesce((select jsonb_agg(jsonb_build_object(
    'id',id,'name',name,'enabled',enabled,'revision',revision,'last_seen_at',last_seen_at,'paired',origin_id is not null,'revoked_at',revoked_at,'revoked_by',revoked_by,'revoked_reason',revoked_reason)
    order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id) from (select * from public.aire_gateways where classroom_id=p_classroom_id order by enabled desc,coalesce(revoked_at,last_seen_at,'epoch'::timestamptz) desc,id limit 50) listed),'[]'::jsonb) else '[]'::jsonb end));
end $$;
revoke all on function public.aire_admin_capabilities(uuid) from public,anon,service_role;
grant execute on function public.aire_admin_capabilities(uuid) to authenticated;
create function aire_private.incident_capabilities(p_incident_id uuid) returns jsonb
language plpgsql stable set search_path='' as $$
declare item public.aire_incidents; duty public.aire_duty; member_role text;
 actor uuid:=auth.uid(); active boolean; operational boolean; coordinator boolean;
 normal boolean; incomplete boolean; eligible boolean; attend boolean; resolve boolean; archive boolean;
begin
 select * into item from public.aire_incidents where id=p_incident_id;
 member_role:=public.aire_role(item.classroom_id);
 select * into duty from public.aire_duty where classroom_id=item.classroom_id;
 active:=coalesce(item.status<>'resuelto',false);
 operational:=coalesce(member_role in ('admin','docente'),false) and actor is not null;
 coordinator:=operational and actor is not distinct from item.coordinator_id and (actor is not distinct from duty.coordinator or actor is not distinct from duty.deputy);
 normal:=exists(select 1 from public.aire_snapshots s where s.gateway_id=item.gateway_id and s.source=item.source and s.state='normal'
  and s.sample_at between now()-interval '95 seconds' and now()+interval '5 seconds'
  and (item.lab_run_id is null or s.observation->>'lab_run_id'=item.lab_run_id::text));
 incomplete:=exists(select 1 from public.aire_instructions where incident_id=item.id and status not in ('reemplazada','realizada'));
 eligible:=exists(select 1 from public.aire_gateways where id=item.gateway_id and not enabled)
  or (item.source='simulacion' and exists(select 1 from public.aire_lab_runs where id=item.lab_run_id and (status in ('finalizado','cancelado','error') or expires_at<=now())));
 attend:=active and operational and (actor is not distinct from duty.teacher or actor is not distinct from item.coordinator_id);
 resolve:=active and coordinator and normal and not incomplete;
 archive:=active and coordinator and eligible;
 return jsonb_build_object('can_attend',attend,'can_resolve',resolve,'can_archive',archive,
  'attend_reason',case when attend then null when not active then 'El incidente ya tiene un cierre registrado' else 'Solo el docente responsable o la coordinación del incidente pueden atender' end,
  'resolve_reason',case when resolve then null when not active then 'El incidente ya tiene un cierre registrado' when not coordinator then 'Solo coordinación vigente puede revisar el cierre' when incomplete then 'Falta el resultado completo de la indicación vigente' else 'Se requiere lectura normal reciente del mismo origen' end,
  'archive_reason',case when archive then null when not active then 'El incidente ya tiene un cierre registrado' when not coordinator then 'Solo coordinación vigente puede archivar' else 'Solo se archiva por retiro del receptor o finalización/vencimiento del ensayo' end);
end $$;
revoke all on function aire_private.incident_capabilities(uuid) from public,anon,authenticated,service_role;

create function public.aire_archive_incident(p_incident_id uuid,p_revision integer,p_note text) returns void
language plpgsql security definer set search_path='' as $$
declare item public.aire_incidents; capabilities jsonb; warning text;
begin
 perform pg_advisory_xact_lock(173034001);
 select * into item from public.aire_incidents where id=p_incident_id for update;
 if auth.uid() is null or public.aire_role(item.classroom_id) not in ('admin','docente') or public.aire_role(item.classroom_id) is null then
  raise exception 'Sin acceso operativo al incidente' using errcode='42501';
 end if;
 if p_note is null or length(trim(p_note)) not between 3 and 500 then raise exception 'Explique el motivo y la acción tomada (3 a 500 caracteres)'; end if;
 if item.status='resuelto' and item.closure_kind='administrativo' and item.closed_by=auth.uid()
  and item.closure_reason=trim(p_note) and p_revision=item.revision-1 then return; end if;
 if item.revision is distinct from p_revision then raise exception 'El incidente cambió; actualice' using errcode='40001'; end if;
 capabilities:=aire_private.incident_capabilities(item.id);
 if not (capabilities->>'can_archive')::boolean then raise exception '%',capabilities->>'archive_reason' using errcode='42501'; end if;
 if pg_database_size(current_database())>=314572800 or (select count(*) from public.aire_coord_events)>=20000 then
  raise exception 'CUOTA_COORDINACION: se requiere mantenimiento del historial antes de continuar';
 end if;
 warning:='ARCHIVO ADMINISTRATIVO · No confirma normalización. Motivo: '||trim(p_note);
 update public.aire_incidents set status='resuelto',closure_kind='administrativo',closed_by=auth.uid(),closed_at=now(),
 closure_reason=trim(p_note),note=warning,revision=revision+1,updated_at=now() where id=item.id;
 -- Retirar indicaciones conservando texto/respuesta: nunca marcarlas como realizadas.
 update public.aire_instructions set status='reemplazada',revision=revision+1 where incident_id=item.id and status not in ('reemplazada','realizada');
 update public.aire_deliveries set status='cancelado',lease_id=null,lease_until=null where incident_id=item.id and status in ('pendiente','reintento');
 insert into public.aire_attention_log(classroom_id,incident_id,actor,action,note) values(item.classroom_id,item.id,auth.uid(),'archivar',warning);
 insert into public.aire_coord_events(incident_id,actor,kind,notification_state,note)
 values(item.id,auth.uid(),'archivo_administrativo','registro_sin_push',warning);
end $$;
revoke all on function public.aire_archive_incident(uuid,integer,text) from public,anon,service_role;
grant execute on function public.aire_archive_incident(uuid,integer,text) to authenticated;
create or replace function public.aire_overview() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 return public.aire_meter_response(jsonb_build_object('classrooms',coalesce((select jsonb_agg(to_jsonb(c)) from public.aire_classrooms c where public.aire_role(c.id) is not null),'[]'::jsonb),
 'memberships',coalesce((select jsonb_agg(to_jsonb(m)) from public.aire_members m where m.user_id=auth.uid()),'[]'::jsonb),
 'snapshots',coalesce((select jsonb_agg(to_jsonb(s)) from public.aire_snapshots s where public.aire_role(s.classroom_id) is not null),'[]'::jsonb),
 'incidents',coalesce((select jsonb_agg(to_jsonb(i)||jsonb_build_object('capabilities',aire_private.incident_capabilities(i.id))) from(select * from public.aire_incidents where public.aire_role(classroom_id) is not null order by opened_at desc limit 30)i),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select id,classroom_id,incident_id,status,attempts,error,received_at,opened_at from public.aire_deliveries where public.aire_role(classroom_id) is not null order by created_at desc limit 50)d),'[]'::jsonb),
 'budget',public.aire_free_budget()));
end $$;
commit;
