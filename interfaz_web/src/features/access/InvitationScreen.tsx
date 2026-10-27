import {useEffect,useState} from 'react';
import {cloudClient} from '../../data/cloud/client';
import {loadPublicConnection} from '../../data/cloud/publicConnection';
import logo from '../../assets/sfa-aire.png';
import '../../cloud.css';
import '../../portal-theme.css';
type Invite={token:string;email:string;activation:string};
function readInvite():Invite|null{
 const values=new URLSearchParams(location.hash.slice(1)),token=values.get('invitacion');
 if(token){const invite={token,email:values.get('correo')||'',activation:values.get('alta')||''};history.replaceState(null,'',location.pathname);sessionStorage.setItem('sfa-pending-invite',JSON.stringify(invite));return invite}
 try{return JSON.parse(sessionStorage.getItem('sfa-pending-invite')||'null')}catch{return null}
}
export default function InvitationScreen(){
 const [invite,setInvite]=useState(readInvite),[link,setLink]=useState(''),[password,setPassword]=useState(''),[confirm,setConfirm]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[ready,setReady]=useState(false);
 useEffect(()=>{loadPublicConnection().then(c=>setReady(!!c)).catch(()=>setNotice('No se pudo cargar la conexión. Compruebe su red y recargue.'))},[]);
 async function accept(e:React.FormEvent){
  e.preventDefault();if(!invite||busy)return;
  if(invite.activation&&(password.length<12||password!==confirm)){setNotice('Use al menos 12 caracteres y confirme la misma contraseña.');return}
  setBusy(true);setNotice('');let client:ReturnType<typeof cloudClient>|undefined;
  try{
   const config=await loadPublicConnection();if(!config)throw Error('Conexión institucional no disponible.');client=cloudClient(config.url,config.key);
   if(invite.activation){
    const {data:current}=await client.auth.getUser();
    if(current.user?.email?.toLowerCase()!==invite.email.toLowerCase()){
     const {data,error}=await client.auth.verifyOtp({token_hash:invite.activation,type:'invite'});
     if(error||!data.user)throw Error('El enlace de alta venció o ya se utilizó. Solicite una invitación nueva.');
     if(data.user.email?.toLowerCase()!==invite.email.toLowerCase())throw Error('El enlace no corresponde al correo indicado.');
    }
    const {error}=await client.auth.updateUser({password});if(error)throw error;
   }else{
    const {error}=await client.auth.signInWithPassword({email:invite.email,password});if(error)throw Error('El correo o la contraseña no coinciden. Use la contraseña de su cuenta existente.');
   }
   const {data,error}=await client.rpc('aire_invite_accept',{p_token:invite.token});if(error)throw Error(error.message);if(data?.accepted!==true)throw Error('No se pudo confirmar el acceso.');
   sessionStorage.removeItem('sfa-pending-invite');setPassword('');setConfirm('');location.replace('/remoto');
  }catch(e){setNotice(e instanceof Error?e.message:String(e));setBusy(false)}finally{void client?.auth.dispose()}
 }
 return <main className="login cloud-login access-layout portal-theme"><section className="access-story"><img className="access-logo" src={logo} alt="SFA Aire"/><p className="eyebrow">INVITACIÓN PRIVADA</p><h1>Tu aula, conectada.</h1><p>Una cuenta propia para consultar las mediciones y recibir los avisos de tus aulas.</p><small>El permiso y el aula los define el administrador.<br/>Después puedes ingresar con esta cuenta en Android.</small></section><section className="access-form"><h2>{invite?.activation?'Activa tu cuenta':invite?'Acepta tu invitación':'Tengo una invitación'}</h2>{notice&&<p className="banner error" role="alert">{notice}</p>}{!invite?<form onSubmit={e=>{e.preventDefault();try{const u=new URL(link);if(!['https:','http:'].includes(u.protocol))throw Error();const p=new URLSearchParams(u.hash.slice(1)),token=p.get('invitacion')||'',email=p.get('correo')||'';if(!/^[a-f0-9]{64}$/.test(token)||!email)throw Error();const i={token,email,activation:p.get('alta')||''};sessionStorage.setItem('sfa-pending-invite',JSON.stringify(i));setInvite(i);setLink('');setNotice('')}catch{setNotice('Pegue el enlace completo que le compartió el administrador.')}}}><p>Pega el enlace privado recibido. El correo por sí solo no habilita el acceso.</p><label>Enlace de invitación<input type="url" required autoComplete="off" value={link} onChange={e=>setLink(e.target.value)}/></label><button>Continuar</button></form>:<form onSubmit={accept}><p>{invite.activation?'Elige tu propia contraseña.':'Ya tienes una cuenta. Ingresa tu contraseña para aceptar el aula.'}</p><label>Correo de la invitación<input type="email" value={invite.email} readOnly autoComplete="username"/></label><label>{invite.activation?'Crea tu contraseña':'Contraseña'}<input type="password" required minLength={invite.activation?12:1} maxLength={128} autoComplete={invite.activation?'new-password':'current-password'} disabled={busy} value={password} onChange={e=>setPassword(e.target.value)}/></label>{invite.activation&&<label>Confirma tu contraseña<input type="password" required minLength={12} maxLength={128} autoComplete="new-password" disabled={busy} value={confirm} onChange={e=>setConfirm(e.target.value)}/></label>}<button disabled={busy||!ready}>{busy?'Confirmando acceso…':invite.activation?'Crear contraseña y entrar':'Aceptar y entrar'}</button></form>}<a href="/remoto" onClick={()=>sessionStorage.removeItem('sfa-pending-invite')}>Volver al inicio de sesión</a></section></main>;
}
