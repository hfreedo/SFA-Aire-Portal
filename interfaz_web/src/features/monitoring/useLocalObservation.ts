import {useEffect,useState} from 'react';
import {localSnapshot,type LocalObservation} from '../../domain/localObservation';
/** Read-only USB view; retains sample time on errors so no old value becomes fresh. */
export function useLocalObservation(room:string,context:string,enabled:boolean,local:(body:Record<string,unknown>)=>Promise<any>){
 const [result,setResult]=useState<{context:string;value:LocalObservation}|null>(null);
 useEffect(()=>{
  if(!enabled||!room)return;
  let cancelled=false,pending=false;
  const refresh=async()=>{
   if(cancelled||pending||document.visibilityState!=='visible')return;pending=true;
   try{
    const response=await local({classroom_id:room,action:'state'});if(cancelled)return;
    const snapshot=localSnapshot(response,room);
    if(response.classroom_id!==room)throw Error('Aula incompatible');
    if(snapshot)setResult({context,value:{snapshot,available:true}});
    else setResult(old=>old?.context===context?{context,value:{...old.value,available:false}}:null);
   }catch{if(!cancelled)setResult(old=>old?.context===context?{context,value:{...old.value,available:false}}:null)}
   finally{pending=false}
  };
  void refresh();const timer=setInterval(()=>void refresh(),1000);
  const visible=()=>void refresh();document.addEventListener('visibilitychange',visible);
  return()=>{cancelled=true;clearInterval(timer);document.removeEventListener('visibilitychange',visible)};
 },[room,context,enabled,local]);
 return enabled&&result?.context===context?result.value:null;
}
