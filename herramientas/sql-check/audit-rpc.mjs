import {createCloudFixture} from './cloud-fixture.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const remote=JSON.parse(await readFile(new URL('../../artifacts/cloud-all-functions-audit.json',import.meta.url),'utf8'));
const db=await createCloudFixture({baseline:true});
try {
 const local=(await db.query(`select n.nspname as schema,p.proname,pg_get_function_identity_arguments(p.oid) as args,
 pg_get_functiondef(p.oid) as definition,has_function_privilege('anon',p.oid,'execute') as anon_execute,
 has_function_privilege('authenticated',p.oid,'execute') as authenticated_execute,
 has_function_privilege('service_role',p.oid,'execute') as service_execute
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where (n.nspname='public' and p.proname like 'aire_%') or n.nspname='aire_private'`)).rows;
 assert.equal(local.length,remote.length,'Function inventory differs');
 const normalized=s=>s.replace(/\s+/g,' ').trim();
 const key=r=>`${r.schema}.${r.proname}(${r.args})`;
 const details=remote.map(r=>{
  const l=local.find(x=>key(x)===key(r));
  return {function:key(r),definition_matches:!!l&&normalized(r.definition)===normalized(l.definition),
   grants_match:!!l&&['anon_execute','authenticated_execute','service_execute'].every(k=>r[k]===l[k]),
   definition_sha256:createHash('sha256').update(normalized(r.definition)).digest('hex')};
 });
 await writeFile(new URL('../../artifacts/cloud-rpc-drift-report.json',import.meta.url),JSON.stringify({scope:'Read-only deployed catalog vs six historical migrations; no business RPC',functions:details},null,2));
 const differences=details.filter(d=>!d.definition_matches||!d.grants_match);
 console.log(JSON.stringify({compared:details.length,differences},null,2));
 assert.equal(differences.length,0,'Inspect deployment drift before activating migrations');
}finally{await db.close()}
