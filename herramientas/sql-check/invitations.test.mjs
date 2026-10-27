import {createCloudFixture} from './cloud-fixture.mjs';
import {randomUUID,randomBytes,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const db=await createCloudFixture(),owner=randomUUID(),teacher=randomUUID(),recipient=randomUUID(),other=randomUUID(),room=randomUUID();let checks=0;
const token=()=>randomBytes(32).toString('hex'),hash=t=>createHash('sha256').update(t).digest('hex');
async function actor(id,role='authenticated'){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id||'']);await db.exec('set role '+role)}
async function rpc(name,args=[]){return(await db.query('select public.'+name+'('+args.map((_,i)=>'$'+(i+1)).join(',')+') v',args)).rows[0].v}
async function deny(fn){await assert.rejects(fn);checks++}
try{
 for(const [id,email] of [[owner,'owner'],[teacher,'teacher'],[recipient,'recipient'],[other,'other']])await db.query('insert into auth.users values($1,$2)',[id,email+'@example.test']);
 await db.query("insert into public.aire_classrooms(id,name,owner_id) values($1,'Aula prueba',$2)",[room,owner]);
 await db.query("insert into public.aire_members values($1,$2,'admin'),($1,$3,'docente')",[room,owner,teacher]);
 const secret=token();for(const id of [teacher,other]){await actor(id);await deny(()=>rpc('aire_invite_create',[room,'recipient@example.test','admin',hash(secret)]));await deny(()=>rpc('aire_invite_list',[room]))}
 await actor(null,'anon');await deny(()=>rpc('aire_invite_accept',[secret]));
 await actor(owner);const invite=await rpc('aire_invite_create',[room,'recipient@example.test','observador',hash(secret)]);assert.equal(invite.activation,false);checks++;
 const list=await rpc('aire_invite_list',[room]);assert.equal(list[0].status,'pendiente');assert.ok(!JSON.stringify(list).includes(hash(secret)));checks++;
 await deny(()=>rpc('aire_invite_create',[room,'recipient@example.test','admin',hash(token())]));
 await deny(()=>db.exec('select * from aire_private.invitations'));
 await actor(other);await deny(()=>rpc('aire_invite_accept',[secret]));await deny(()=>rpc('aire_invite_revoke',[invite.id]));
 await actor(recipient);const accepted=await rpc('aire_invite_accept',[secret]);assert.equal(accepted.accepted,true);checks++;
 assert.equal((await rpc('aire_invite_accept',[secret])).accepted,true);checks++;
 await db.exec('reset role');assert.equal((await db.query('select role from public.aire_members where classroom_id=$1 and user_id=$2',[room,recipient])).rows[0].role,'observador');checks++;
 await actor(owner);const secret2=token(),revoked=await rpc('aire_invite_create',[room,'other@example.test','docente',hash(secret2)]);await rpc('aire_invite_revoke',[revoked.id]);await actor(other);await deny(()=>rpc('aire_invite_accept',[secret2]));
 await actor(owner);const secret3=token(),expired=await rpc('aire_invite_create',[room,'other@example.test','docente',hash(secret3)]);await db.exec('reset role');await db.query("update aire_private.invitations set expires_at=now()-interval '1 second' where id=$1",[expired.id]);await actor(other);await deny(()=>rpc('aire_invite_accept',[secret3]));
 await actor(owner);const secret4=token(),creatorLost=await rpc('aire_invite_create',[room,'other@example.test','docente',hash(secret4)]);await db.exec('reset role');await db.query("update public.aire_members set role='docente' where user_id=$1",[owner]);await actor(other);await deny(()=>rpc('aire_invite_accept',[secret4]));
 await db.exec('reset role');await db.query("update public.aire_members set role='admin' where user_id=$1",[owner]);await actor(owner);
 for(let i=0;i<6;i++)await rpc('aire_invite_create',[room,`new${i}@example.test`,'docente',hash(token())]);
 await deny(()=>rpc('aire_invite_create',[room,'extra@example.test','docente',hash(token())]));
 console.log(`PASS ${checks}: roles, privacidad, correo, uso único/idempotencia, revocación, vencimiento, creador retirado y cuota diaria.`);
}finally{await db.close()}
