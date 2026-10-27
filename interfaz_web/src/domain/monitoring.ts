/** Reglas de presentación compartidas por el portal y el receptor; no autoriza acciones. */
export const stateLabels:Record<string,string>={normal:'Sin variación sostenida',aviso:'Variación sostenida',alerta:'Revisar ambiente',fallo_sensor:'Revisar sensores',calentando:'Estabilizando sensor',sin_calibrar:'Falta referencia',sin_datos:'Sin datos recientes',detenido:'Monitoreo detenido'};
export function freshness(sampleAt:string,now:number){
 const elapsed=(now-Date.parse(sampleAt))/1000;
 return {fresh:Number.isFinite(elapsed)&&elapsed>=-5&&elapsed<=95,age:Number.isFinite(elapsed)?Math.max(0,Math.round(elapsed)):null};
}
export function canAttend(role:string|undefined,online:boolean,demo:boolean,busy:boolean){return online&&!demo&&!busy&&(role==='admin'||role==='docente')}
export function incidentMatches(status:string,filter:string){return filter==='todos'||(filter==='resueltos'?status==='resuelto':status!=='resuelto')}

export type IncidentAction='atender'|'resolver'|'archivar';
export function archivedIncident(item:{closure_kind?:string|null}){return item.closure_kind==='administrativo'}
export function incidentInFilter(item:{status:string;closure_kind?:string|null},filter:string){
 if(filter==='todos')return true;
 if(filter==='archivados')return archivedIncident(item);
 if(filter==='resueltos')return item.status==='resuelto';
 return item.status!=='resuelto';
}
export function incidentAction(item:{status:string;capabilities?:{can_attend?:unknown;can_resolve?:unknown;can_archive?:unknown;attend_reason?:string|null;resolve_reason?:string|null;archive_reason?:string|null}},action:IncidentAction,context:{online:boolean;demo:boolean;busy:boolean}){
 if(context.demo)return {allowed:false,reason:'Demostración: no se guardan cambios.'};
 if(!context.online)return {allowed:false,reason:'Sin conexión verificada. Actualice el estado.'};
 if(context.busy)return {allowed:false,reason:'Espere a que termine la operación actual.'};
 if(item.status==='resuelto')return {allowed:false,reason:'El incidente ya está cerrado.'};
 const caps=item.capabilities;
 if(!caps||![caps.can_attend,caps.can_resolve,caps.can_archive].every(value=>typeof value==='boolean'))return {allowed:false,reason:'Faltan capacidades verificadas. Actualice el portal y el servidor.'};
 const flag=action==='atender'?caps.can_attend:action==='resolver'?caps.can_resolve:caps.can_archive;
 const reason=action==='atender'?caps.attend_reason:action==='resolver'?caps.resolve_reason:caps.archive_reason;
 return {allowed:flag===true,reason:flag===true?'':reason||'Esta acción no está disponible para su responsabilidad actual.'};
}
