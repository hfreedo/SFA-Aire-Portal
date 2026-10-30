import {createCloudFixture} from './cloud-fixture.mjs';
import {readFile} from 'node:fs/promises';import {randomUUID as uuid} from 'node:crypto';import assert from 'node:assert/strict';
const db=await createCloudFixture();let checks=0;
const owner=uuid(),admin=uuid(),teacher=uuid(),outsider=uuid(),room=uuid();
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function denied(fn){await assert.rejects(fn);checks++}
try{
 for(const [id,label] of [[owner,'owner'],[admin,'admin'],[teacher,'teacher'],[outsider,'other']])await db.query('insert into auth.users values($1,$2)',[id,label+'@test.invalid']);
 await db.query("insert into public.aire_classrooms(id,name,school,owner_id) values($1,'Aula prueba','Institución',$2)",[room,owner]);
 for(const [id,role] of [[owner,'admin'],[admin,'admin'],[teacher,'docente']])await db.query('insert into public.aire_members values($1,$2,$3)',[room,id,role]);
 for(const id of [teacher,outsider]){await actor(id);await denied(()=>rpc('aire_classroom_admin',[room]));await denied(()=>rpc('aire_update_classroom',[room,1,'Otro nombre','Otra institución']));await denied(()=>rpc('aire_grant_member',[room,'other@test.invalid','admin']));await denied(()=>rpc('aire_remove_member',[room,teacher]))}
 await actor(null,'anon');await denied(()=>rpc('aire_classroom_admin',[room]));
 await actor(admin);const data=await rpc('aire_classroom_admin',[room]);assert.equal(data.members.length,3);assert.equal(data.classroom.revision,1);assert.equal(data.can_manage_members,true);assert.ok(!JSON.stringify(data).includes('secret'));checks++;
 const caps=await rpc('aire_admin_capabilities',[room]);assert.equal(caps.can_manage_members,true);checks++;
 await rpc('aire_update_classroom',[room,1,'Aula editada','Institución clara']);checks++;
 await denied(()=>rpc('aire_update_classroom',[room,1,'Escritura atrasada','No']));
 await denied(()=>rpc('aire_update_classroom',[room,2,'x','No']));
 const edited=await rpc('aire_classroom_admin',[room]);assert.equal(edited.classroom.name,'Aula editada');assert.equal(edited.classroom.revision,2);checks++;
 await rpc('aire_grant_member',[room,'other@test.invalid','docente']);checks++;
 await rpc('aire_grant_member',[room,'teacher@test.invalid','observador']);checks++;
 await denied(()=>rpc('aire_grant_member',[room,'owner@test.invalid','observador']));await denied(()=>rpc('aire_grant_member',[room,'admin@test.invalid','observador']));
 await denied(()=>rpc('aire_remove_member',[room,owner]));await denied(()=>rpc('aire_remove_member',[room,admin]));
 await actor(outsider);await rpc('aire_register_phone',[room,uuid(),'fixture-token-1234567890','Teléfono de prueba',false]);
 await actor(admin);assert.equal((await rpc('aire_classroom_admin',[room])).members.find(m=>m.id===outsider).phone_count,1);checks++;
 await rpc('aire_remove_member',[room,outsider]);checks++;
 await actor(outsider);await denied(()=>rpc('aire_overview',[]).then(value=>{assert.equal(value.classrooms.length,1)})); // No aula disponible al retirarse.
 await db.exec('reset role');assert.equal((await db.query('select count(*)::int n from public.aire_phones where user_id=$1',[outsider])).rows[0].n,0);checks++;
 console.log('PASS: '+checks+' comprobaciones de administración, límites de aula/rol, edición y retirada de acceso; sin nube.');
}finally{await db.close()}
