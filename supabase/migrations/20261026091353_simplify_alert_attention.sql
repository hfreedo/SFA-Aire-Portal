-- Atención sencilla. Cerrar el aviso es una decisión humana, no una medición.
-- Contrato compatible: resolver/resuelto se conservan para clientes anteriores.
begin;
alter table public.aire_incidents drop constraint aire_incidents_closure_kind_check;
alter table public.aire_incidents add constraint aire_incidents_closure_kind_check
 check(closure_kind in ('administrativo','normalizacion','atendido'));

create or replace function aire_private.incident_capabilities(p_incident_id uuid) returns jsonb
language plpgsql stable set search_path='' as $$
declare item public.aire_incidents; permitted boolean; reason text;
begin
 select * into item from public.aire_incidents where id=p_incident_id;
 permitted:=coalesce(auth.uid() is not null and public.aire_role(item.classroom_id) in ('admin','docente') and item.status<>'resuelto',false);
 reason:=case when item.status='resuelto' then 'Este aviso ya fue atendido' else 'Solo docentes y administradores del aula pueden registrar atención' end;
 return jsonb_build_object('can_attend',permitted,'can_resolve',permitted,'can_archive',false,
 'attend_reason',case when permitted then null else reason end,
 'resolve_reason',case when permitted then null else reason end,
 'archive_reason','Use Marcar atendido. No se requiere un archivo especial');
end $$;

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
   where incident_id=item.id and status in ('pendiente','reintento');
 end if;
 -- Sin comunicaciones ni nuevas notificaciones de coordinación implícitas.
end $$;
revoke all on function public.aire_attention(uuid,integer,text,text) from public,anon,service_role;
grant execute on function public.aire_attention(uuid,integer,text,text) to authenticated;
create or replace function public.aire_overview() returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null then raise exception 'Inicie sesión' using errcode='42501'; end if;
 return public.aire_meter_response(jsonb_build_object('attention_contract',2,'classrooms',coalesce((select jsonb_agg(to_jsonb(c)) from public.aire_classrooms c where public.aire_role(c.id) is not null),'[]'::jsonb),
 'memberships',coalesce((select jsonb_agg(to_jsonb(m)) from public.aire_members m where m.user_id=auth.uid()),'[]'::jsonb),
 'snapshots',coalesce((select jsonb_agg(to_jsonb(s)) from public.aire_snapshots s where public.aire_role(s.classroom_id) is not null),'[]'::jsonb),
 'incidents',coalesce((select jsonb_agg(to_jsonb(i)||jsonb_build_object('capabilities',aire_private.incident_capabilities(i.id))) from(select * from public.aire_incidents where public.aire_role(classroom_id) is not null order by opened_at desc limit 30)i),'[]'::jsonb),
 'deliveries',coalesce((select jsonb_agg(to_jsonb(d)) from(select id,classroom_id,incident_id,status,attempts,error,received_at,opened_at from public.aire_deliveries where public.aire_role(classroom_id) is not null order by created_at desc limit 50)d),'[]'::jsonb),
 'budget',public.aire_free_budget()));
end $$;

commit;
