import {PGlite} from '@electric-sql/pglite';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';

export async function freshChecks(){
 const fresh=new PGlite();let checks=0;
 try{
  await fresh.exec(`create role anon;create role authenticated;create schema auth;
   create table auth.users(id uuid primary key,email text);
   create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
   grant usage on schema auth to authenticated,anon;
   insert into auth.users values('51515151-5151-4151-8151-515151515151','owner@example.test');`);
  for(const file of ['202610240001_aire_cloud.sql','202610240002_admin_lab_free.sql','202610240003_coordination.sql','202610240004_notification_reserve.sql']){
   await fresh.exec(await readFile(new URL('../../supabase/migrations/'+file,import.meta.url),'utf8'));checks++;
  }
  await fresh.exec("select set_config('request.jwt.claim.sub','51515151-5151-4151-8151-515151515151',false);set role authenticated");
  await assert.rejects(()=>fresh.query("select public.aire_create_classroom('Sin habilitación','Escuela')"));checks++;
  await fresh.exec("reset role;insert into public.aire_creators values('51515151-5151-4151-8151-515151515151');set role authenticated");
  await fresh.query("select public.aire_create_classroom('Primera aula','Escuela')");
  const view=(await fresh.query('select public.aire_overview() as data')).rows[0].data;
  assert.equal(view.classrooms.length,1);assert.equal(view.budget.operational_push_today,0);assert.equal(view.budget.laboratory_push_today,0);checks++;
  await assert.rejects(()=>fresh.query('select * from public.aire_free_usage'));checks++;
  return checks;
 }finally{await fresh.close()}
}
