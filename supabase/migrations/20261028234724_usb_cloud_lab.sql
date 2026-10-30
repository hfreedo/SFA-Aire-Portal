begin;
alter table public.aire_lab_runs add column input_source text not null default 'generated' check(input_source in ('generated','usb'));
create function public.aire_lab_start_usb(p_classroom_id uuid,p_gateway_id uuid,p_run_id uuid,p_allow_push boolean default true,p_free_plan_confirmed boolean default false) returns uuid
language plpgsql security definer set search_path='' as $$
declare result uuid; previous public.aire_lab_runs;
begin
 if public.aire_role(p_classroom_id) is distinct from 'admin' then raise exception 'Solo administradores pueden iniciar pruebas' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(173034001);
 select * into previous from public.aire_lab_runs where id=p_run_id;
 if found and previous.input_source!='usb' then raise exception 'ID utilizado por otra modalidad de prueba'; end if;
 -- Conserva autorización, idempotencia, reservas, teléfonos, cuotas y plan gratuito.
 result:=public.aire_lab_start(p_classroom_id,p_gateway_id,p_run_id,25,55,700,180,p_allow_push,false,p_free_plan_confirmed);
 update public.aire_lab_runs set input_source='usb' where id=result;
 return result;
end $$;
revoke all on function public.aire_lab_start_usb(uuid,uuid,uuid,boolean,boolean) from public,anon;
grant execute on function public.aire_lab_start_usb(uuid,uuid,uuid,boolean,boolean) to authenticated;
commit;
