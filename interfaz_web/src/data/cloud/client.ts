import {createClient} from '@supabase/supabase-js';
export function publicConfig(url:string,key:string){
 const parsed=new URL(url);
 if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.search||parsed.hash||!['','/'].includes(parsed.pathname))throw Error('Use la URL base HTTPS de su proyecto Supabase.');
 if(key.startsWith('sb_secret_'))throw Error('Use la clave pública publishable; nunca una clave secreta.');
 if(key.startsWith('eyJ')){let claims;try{claims=JSON.parse(atob(key.split('.')[1].replaceAll('-','+').replaceAll('_','/')))}catch{throw Error('Clave pública inválida.')};if(claims.role!=='anon')throw Error('Se requiere la clave anon pública, nunca service_role.');}
 else if(!key.startsWith('sb_publishable_'))throw Error('La clave debe ser publishable o anon pública.');
 return {url:parsed.origin,key};
}
export function cloudStorageKey(url:string){return 'sfa-aire-'+new URL(url).host}
export function cloudClient(url:string,key:string){
 const config=publicConfig(url,key);
 return createClient(config.url,config.key,{auth:{persistSession:true,storage:sessionStorage,storageKey:cloudStorageKey(config.url),autoRefreshToken:true,detectSessionInUrl:false}});
}
