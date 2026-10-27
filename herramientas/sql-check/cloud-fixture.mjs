import {PGlite} from '@electric-sql/pglite';
import {readFile,readdir} from 'node:fs/promises';

// Infraestructura exclusivamente local. Vault, red y cron son dobles sin secretos ni envíos.
export async function createCloudFixture({baseline=false,through=null}={}) {
 const db=new PGlite();
 await db.exec(`create role anon;create role authenticated;create role service_role;
 create schema auth;create table auth.users(id uuid primary key,email text);
 create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
 grant usage on schema auth to anon,authenticated;
 create schema vault;create table vault.decrypted_secrets(id uuid primary key,decrypted_secret text,name text);
 create function vault.create_secret(secret text,label text) returns uuid language plpgsql as $$declare i uuid:=gen_random_uuid();begin insert into vault.decrypted_secrets values(i,secret,label);return i;end$$;
 create function vault.update_secret(i uuid,secret text) returns void language sql as $$update vault.decrypted_secrets set decrypted_secret=secret where id=i$$;
 create schema net;create schema cron;
 create table net.test_requests(id bigint generated always as identity,url text,headers jsonb,body jsonb);
 create function net.http_post(url text,headers jsonb,body jsonb,timeout_milliseconds integer) returns bigint language plpgsql as $$declare i bigint;begin insert into net.test_requests(url,headers,body) values(url,headers,body) returning id into i;return i;end$$;
 create function cron.schedule(label text,expression text,command text) returns bigint language sql as $$select 1::bigint$$;`);
 const directory=new URL('../../supabase/migrations/',import.meta.url);
 try {
  for(const file of (await readdir(directory)).filter(f=>f.endsWith('.sql')).sort()) {
   if(through&&file>through)continue;
   if(baseline&&file>'20261025021637_cloud_push_scheduler.sql')continue;
   const sql=await readFile(new URL(file,directory),'utf8');
   await db.exec(sql.replace(/^create extension[^;]+;/gm,''));
  }
  return db;
 }catch(error){await db.close();throw error;}
}
