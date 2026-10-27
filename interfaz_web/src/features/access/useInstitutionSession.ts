import {useEffect,useState,useSyncExternalStore} from 'react';
import {CloudSession} from '../../application/session/CloudSession';
import {sessionPort,clearSessionCache} from '../../data/cloud/sessionPort';
import {loadPublicConnection} from '../../data/cloud/publicConnection';

export function useInstitutionSession(preview:boolean){
 const [service]=useState(()=>new CloudSession(sessionPort,clearSessionCache));
 const state=useSyncExternalStore(service.subscribe,service.getSnapshot);
 useEffect(()=>{
  const controller=new AbortController();
  loadPublicConnection(controller.signal).then(config=>{if(!controller.signal.aborted)service.configure(config,preview)}).catch(error=>{if(!controller.signal.aborted)service.failConfiguration(error instanceof Error?error.message:String(error))});
  return()=>{controller.abort();service.dispose()};
 },[service]);
 return {state,service};
}
