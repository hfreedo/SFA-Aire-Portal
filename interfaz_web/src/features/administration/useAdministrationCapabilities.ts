import {useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {administrationCapabilities,type AdministrationCapabilities} from '../../domain/administration';
import {ResultScope} from '../../application/workspace/ResultScope';
import type {Rpc} from '../../application/workspace/ClassroomAdministration';

export type AdministrationState={data:AdministrationCapabilities|null;ready:boolean;loading:boolean;error:string};
export function useAdministrationCapabilities(rpc:Rpc,room:string,contextKey:string,enabled:boolean){
 const [scope]=useState(()=>new ResultScope());scope.select(contextKey);
 const [state,setState]=useState<{key:string;data:AdministrationCapabilities|null;loading:boolean;error:string}>({key:contextKey,data:null,loading:false,error:''});
 const request=useRef(0);
 useLayoutEffect(()=>{scope.activate();return()=>scope.dispose()},[scope]);
 const reload=useCallback(async()=>{
  if(!enabled)return;
  const ticket=scope.capture(),version=++request.current;
  setState(old=>({key:contextKey,data:old.key===contextKey?old.data:null,loading:true,error:''}));
  try{const data=administrationCapabilities(await rpc('aire_admin_capabilities',{p_classroom_id:room||null}),room||null);if(scope.accepts(ticket)&&version===request.current)setState({key:contextKey,data,loading:false,error:''})}
  catch(error){if(scope.accepts(ticket)&&version===request.current)setState({key:contextKey,data:null,loading:false,error:error instanceof Error?error.message:String(error)})}
 },[rpc,room,contextKey,enabled,scope]);
 useEffect(()=>{if(enabled)void reload();else {request.current++;setState({key:contextKey,data:null,loading:false,error:''})}},[enabled,reload,contextKey]);
 const current=state.key===contextKey?state:{data:null,loading:enabled,error:''};
 return {state:{data:current.data,loading:current.loading,error:current.error,ready:enabled&&!current.loading&&!current.error&&!!current.data} as AdministrationState,reload};
}
