import {hostedPortal} from './publicConnection';
import {cloudClient,cloudStorageKey} from './client';
import type {PublicConnection,SessionPort} from '../../application/session/CloudSession';

export function clearSessionCache(connection:PublicConnection){const key=cloudStorageKey(connection.url);sessionStorage.removeItem(key);sessionStorage.removeItem(key+'-code-verifier')}

/** Único adaptador de autenticación/RPC del SDK; cada solicitud conserva su identidad. */
export function sessionPort(connection:PublicConnection):SessionPort {
 const client=cloudClient(connection.url,connection.key);let disposed=false;
 return {
  subscribe(listener){const {data}=client.auth.onAuthStateChange((_event,session)=>listener(session?.user.id||null));return()=>data.subscription.unsubscribe()},
  async restore(){const {data,error}=await client.auth.getSession();if(error)throw error;return data.session?.user.id||null},
  async signIn(email,password){const {data,error}=await client.auth.signInWithPassword({email,password});if(error)throw error;if(!data.session||!data.user)throw Error('No se pudo verificar la sesión.');return data.user.id},
  async signOut(){const {error}=await client.auth.signOut({scope:'local'});if(error)throw error},
  async rpc(name,args,actor){const {data:auth,error:sessionError}=await client.auth.getSession();if(sessionError)throw sessionError;if(disposed||!auth.session||auth.session.user.id!==actor)throw Error('La sesión cambió.');const {data,error}=await client.rpc(name,args).setHeader('Authorization','Bearer '+auth.session.access_token);if(error)throw Error(error.message);return data},
  async local(body,actor){if(hostedPortal)throw Error('La conexión USB se realiza desde el panel instalado en la PC del Arduino.');const {data:auth,error}=await client.auth.getSession();if(error)throw error;if(disposed||!auth.session||auth.session.user.id!==actor)throw Error('La sesión cambió.');const r=await fetch('/api/workspace/local',{method:'POST',headers:{Authorization:'Bearer '+auth.session.access_token,'Content-Type':'application/json'},body:JSON.stringify(body),redirect:'error'});const data=await r.json().catch(()=>null);if(!r.ok)throw Error(typeof data?.detail==='string'?data.detail:'No se pudo comunicar con el receptor de esta PC.');return data},
  async invoke(name,body,actor){const {data:auth,error:sessionError}=await client.auth.getSession();if(sessionError)throw sessionError;if(disposed||!auth.session||auth.session.user.id!==actor)throw Error('La sesión cambió.');const {data,error}=await client.functions.invoke(name,{body,headers:{Authorization:'Bearer '+auth.session.access_token}});if(error){const response=error.context;if(response instanceof Response){const detail=await response.json().catch(()=>null);if(detail?.message)throw Error(detail.message)}throw Error('No se pudo guardar la cuenta. Actualice las personas antes de reintentar.')}return data},
  dispose(){disposed=true;void client.auth.dispose()},
  clearLocal(){clearSessionCache(connection)}
 };
}
