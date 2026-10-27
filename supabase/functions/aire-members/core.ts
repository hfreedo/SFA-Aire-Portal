type Config={url:string;publicKey:string;secret:string};
const cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization, apikey, content-type, x-client-info','Access-Control-Allow-Methods':'POST, OPTIONS','Content-Type':'application/json'};
const reply=(status:number,message:string,extra={})=>new Response(JSON.stringify({message,...extra}),{status,headers:cors});
export async function handleMembers(req:Request,config:Config,send:typeof fetch=fetch):Promise<Response>{
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
 if(req.method!=='POST')return reply(405,'Método no disponible.');
 const auth=req.headers.get('authorization')||'';
 if(!/^Bearer [A-Za-z0-9_.-]+$/.test(auth))return reply(401,'Inicie sesión.');
 if(!config.url||!config.publicKey||!config.secret)return reply(503,'La gestión de cuentas aún no está configurada.');
 let body:any;
 try{const reader=req.body?.getReader();let value='',size=0;const decoder=new TextDecoder();if(!reader)return reply(400,'Complete los datos.');
 while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>8192){await reader.cancel();return reply(413,'Formulario demasiado grande.')}value+=decoder.decode(part.value,{stream:true})}
 value+=decoder.decode();body=JSON.parse(value)}catch{return reply(400,'Formulario inválido.')}
 if(!body||typeof body!=='object'||Object.keys(body).some(k=>!['classroom_id','email','role','password'].includes(k)))return reply(400,'Formulario inválido.');
 const room=body.classroom_id,email=typeof body.email==='string'?body.email.trim().toLowerCase():'',role=body.role;
 if(typeof room!=='string'||!/^[0-9a-f-]{36}$/i.test(room)||!email||email.length>254||!/^\S+@\S+\.\S+$/.test(email)||!['admin','docente','observador'].includes(role))return reply(400,'Revise aula, correo y rol.');
 const rpc=async(name:string,args:unknown)=>{
  const r=await send(config.url+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:config.publicKey,Authorization:auth,'Content-Type':'application/json'},body:JSON.stringify(args),redirect:'error',signal:AbortSignal.timeout(10000)});
  const data=await r.json().catch(()=>({}));return {ok:r.ok,status:r.status,data};
 };
 try{
  const identity=await send(config.url+'/auth/v1/user',{headers:{apikey:config.publicKey,Authorization:auth},redirect:'error',signal:AbortSignal.timeout(10000)});
  if(!identity.ok)return reply(401,'Inicie sesión nuevamente.');
  const user=await identity.json().catch(()=>null);if(typeof user?.id!=='string'||!user.id)return reply(401,'Inicie sesión nuevamente.');
  const access=await rpc('aire_classroom_admin',{p_classroom_id:room});
  if(!access.ok||access.data?.classroom?.id!==room||access.data?.can_manage_members!==true)return reply(403,'No tiene permiso para gestionar personas en esta aula.');
  const args={p_classroom_id:room,p_email:email,p_role:role};
  let assigned=await rpc('aire_grant_member',args);
  if(assigned.ok)return reply(200,'Cuenta vinculada al aula.',{created:false});
  if(assigned.data?.message!=='ACCOUNT_NOT_FOUND')return reply(409,'No se pudo asignar la cuenta. Actualice las personas del aula.');
  if(typeof body.password!=='string'||body.password.length<12||body.password.length>128)return reply(400,'La cuenta no existe. Elija Crear cuenta nueva e indique una contraseña inicial de 12 a 128 caracteres.',{code:'ACCOUNT_NOT_FOUND'});
  if(!access.data.account_creation_available||access.data.members.length>=access.data.member_limit)return reply(409,'Se alcanzó una guarda preventiva de cuentas. Revise las personas registradas.');
  const created=await send(config.url+'/auth/v1/admin/users',{method:'POST',headers:{apikey:config.secret,Authorization:'Bearer '+config.secret,'Content-Type':'application/json'},body:JSON.stringify({email,password:body.password,email_confirm:true}),redirect:'error',signal:AbortSignal.timeout(10000)});
  if(!created.ok)return reply(409,'No se pudo crear la cuenta. Revise el correo y los requisitos de contraseña. Si ya existe, vincúlela como cuenta existente.');
  assigned=await rpc('aire_grant_member',args);
  if(!assigned.ok)return reply(409,'La cuenta se creó, pero no pudo vincularse. Reintente como cuenta existente.',{code:'ACCOUNT_CREATED_NOT_ASSIGNED'});
  return reply(200,'Cuenta creada y vinculada al aula.',{created:true});
 }catch{return reply(503,'No se pudo conectar con la gestión de cuentas. Actualice las personas antes de reintentar.');}
}
