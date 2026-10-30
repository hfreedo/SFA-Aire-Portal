import type {CloudSnapshot} from './models';
export type LocalObservation={snapshot:CloudSnapshot;available:boolean};
export type DisplaySnapshot=CloudSnapshot&{local?:{available:boolean}};
/** Presentation only: never changes cloud records, incidents or alert rules. */
export function mergeLocalObservation(snapshots:CloudSnapshot[],local:LocalObservation|null,room:string):DisplaySnapshot[]{
 if(!local||local.snapshot.classroom_id!==room)return snapshots;
 const current={...local.snapshot,local:{available:local.available}};
 return [...snapshots.filter(s=>s.gateway_id!==current.gateway_id||s.source!==current.source),current];
}
export function localSnapshot(value:any,room:string):CloudSnapshot|null{
 if(value?.classroom_id!==room||typeof value.gateway_id!=='string'||!value.gateway_id||!['arduino','simulacion'].includes(value.source))return null;
 const sample=value.latest;
 if(!sample||sample.source!==value.source||!Number.isFinite(sample.received)||!Number.isFinite(sample.mq_raw)||typeof sample.dht_ok!=='boolean'||typeof sample.state!=='string')return null;
 const date=new Date(sample.received*1000);if(!Number.isFinite(date.getTime()))return null;
 return {classroom_id:room,gateway_id:value.gateway_id,source:value.source,sample_at:date.toISOString(),state:sample.state,observation:{mq_raw:sample.mq_raw,temperature:sample.dht_ok?sample.temperature:null,humidity:sample.dht_ok?sample.humidity:null,dht_ok:sample.dht_ok,ratio:sample.ratio??null,usb_simulation:sample.usb_simulation===true,usb_cloud:sample.usb_cloud===true}};
}

export function localReadingFresh(s:DisplaySnapshot,now:number){
 const age=(now-Date.parse(s.sample_at))/1000;
 return !!s.local?.available&&Number.isFinite(age)&&age>=-5&&age<=10;
}
