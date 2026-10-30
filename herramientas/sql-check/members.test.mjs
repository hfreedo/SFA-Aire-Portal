import {test} from 'node:test';import assert from 'node:assert/strict';import {handleMembers} from '../../supabase/functions/aire-members/core.ts';
const config={url:'https://example.supabase.co',publicKey:'public-fixture',secret:'server-fixture'};
const room='11111111-1111-4111-8111-111111111111';
function request(body={},auth=true){return new Request('https://example.supabase.co/functions/v1/aire-members',{method:'POST',headers:{'Content-Type':'application/json',...(auth?{Authorization:'Bearer fixture.jwt.token'}:{})},body:JSON.stringify(body)})}
function transport({allowed=true,exists=false,full=false,accountCap=true,failAssignment=false}={}){
 const calls=[];let created=false;
 return {calls,send:async(url,options)=>{
  const data=options.body?JSON.parse(options.body):null;calls.push({url,method:options.method,headers:options.headers,data});
  if(url.endsWith('/auth/v1/user'))return Response.json({id:'actor-fixture'});
  if(url.endsWith('/aire_classroom_admin'))return Response.json({classroom:{id:room},can_manage_members:allowed,members:Array(full?10:1).fill({}),member_limit:10,account_creation_available:accountCap});
  if(url.endsWith('/aire_grant_member'))return exists||created&&!failAssignment?Response.json(null):Response.json({message:created?'Permission changed':'ACCOUNT_NOT_FOUND'},{status:400});
  if(url.endsWith('/auth/v1/admin/users')){created=true;return Response.json({id:'fixture-new-user'})}
  throw Error('Unexpected URL')
 }};
}
const body={classroom_id:room,email:'teacher@example.test',role:'docente',password:'Fixture-only-password-2026'};
test('sin sesión no se consulta Auth ni RPC',async()=>{const t=transport();assert.equal((await handleMembers(request(body,false),config,t.send)).status,401);assert.equal(t.calls.length,0)});
test('solo administrador del aula puede crear y asignar',async()=>{const t=transport({allowed:false});assert.equal((await handleMembers(request(body),config,t.send)).status,403);assert.equal(t.calls.length,2)});
test('cuenta nueva se crea con secreto solo en servidor y se asigna con JWT del actor',async()=>{const t=transport();const r=await handleMembers(request(body),config,t.send);assert.equal(r.status,200);assert.equal((await r.json()).created,true);assert.equal(t.calls.length,5);const auth=t.calls.find(c=>c.url.endsWith('/admin/users'));assert.equal(auth.headers.Authorization,'Bearer server-fixture');assert.equal(auth.data.password,body.password);assert.ok(t.calls.filter(c=>c.url.includes('/rpc/')).every(c=>c.headers.Authorization==='Bearer fixture.jwt.token'))});
test('cuenta existente no cambia contraseña ni crea otra identidad',async()=>{const t=transport({exists:true});const r=await handleMembers(request(body),config,t.send);assert.equal(r.status,200);assert.equal(t.calls.length,3);assert.equal((await r.json()).created,false)});
test('sin contraseña no crea cuentas cuando el correo no existe',async()=>{const t=transport();const r=await handleMembers(request({...body,password:undefined}),config,t.send);assert.equal(r.status,400);assert.equal(t.calls.length,3)});
test('guardas de personas y cuentas impiden creación privilegiada',async()=>{for(const options of [{full:true},{accountCap:false}]){const t=transport(options);assert.equal((await handleMembers(request(body),config,t.send)).status,409);assert.ok(t.calls.every(c=>!c.url.includes('/admin/users')))}});
test('si cambia el permiso tras crear, se informa cuenta pendiente sin borrar identidad',async()=>{const t=transport({failAssignment:true});const r=await handleMembers(request(body),config,t.send);assert.equal(r.status,409);assert.equal((await r.json()).code,'ACCOUNT_CREATED_NOT_ASSIGNED');assert.ok(t.calls.every(c=>c.method!=='DELETE'))});
test('tamaño y campos inesperados se rechazan antes de autorizar',async()=>{for(const data of [{...body,secret:'not-allowed'},{...body,password:'x'.repeat(9000)}]){const t=transport();const r=await handleMembers(request(data),config,t.send);assert.ok([400,413].includes(r.status));assert.equal(t.calls.length,0)}});

test('JWT inválido se rechaza en Auth antes de leer aulas o crear cuentas',async()=>{
 const calls=[];const send=async(url)=>{calls.push(url);return Response.json({error:'invalid token'},{status:401})};
 assert.equal((await handleMembers(request(body),config,send)).status,401);assert.deepEqual(calls,[config.url+'/auth/v1/user']);
});
