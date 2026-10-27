-- Contrato FCM v2: identificación opaca del registro de sesión, sin user_id en payload.
begin;
create function aire_private.bind_notification_jobs(p_result jsonb) returns jsonb
language sql stable set search_path='' as $$
 select p_result || jsonb_build_object('jobs',coalesce((
   select jsonb_agg(j.value || jsonb_build_object('installation_id',d.installation_id) order by j.ordinality)
   from jsonb_array_elements(p_result->'jobs') with ordinality j(value,ordinality)
   join public.aire_deliveries d on d.id=(j.value->>'id')::uuid
 ),'[]'::jsonb))
$$;
revoke all on function aire_private.bind_notification_jobs(jsonb) from public,anon,authenticated,service_role;

alter function public.aire_cloud_claim() rename to aire_cloud_claim_v06;
revoke all on function public.aire_cloud_claim_v06() from public,anon,authenticated,service_role;
create function public.aire_cloud_claim() returns jsonb
language sql security definer set search_path='' as $$
 select aire_private.bind_notification_jobs(public.aire_cloud_claim_v06())
$$;
revoke all on function public.aire_cloud_claim() from public,anon,authenticated;
grant execute on function public.aire_cloud_claim() to service_role;

alter function public.aire_claim_push(uuid,text) rename to aire_claim_push_v06;
revoke all on function public.aire_claim_push_v06(uuid,text) from public,anon,authenticated,service_role;
create function public.aire_claim_push(p_gateway_id uuid,p_secret text) returns jsonb
language sql security definer set search_path='' as $$
 select aire_private.bind_notification_jobs(public.aire_claim_push_v06(p_gateway_id,p_secret))
$$;
revoke all on function public.aire_claim_push(uuid,text) from public,service_role;
grant execute on function public.aire_claim_push(uuid,text) to anon,authenticated;
commit;
