import {publicConfig} from './client';
export const hostedPortal=import.meta.env.VITE_HOSTED_PORTAL==='1';
export async function loadPublicConnection(signal?:AbortSignal){
 const response=await fetch(hostedPortal?'/public-config.json':'/api/public-config',{signal,cache:'no-store'});
 if(!response.ok)throw Error('No se pudo cargar la conexión institucional.');
 const config=await response.json();return config?.configured?publicConfig(config.url,config.key):null;
}
