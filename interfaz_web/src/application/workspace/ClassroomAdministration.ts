export type Rpc=(name:string,args?:Record<string,unknown>)=>Promise<any>;
export type GatewayPair={gateway_id:string;gateway_secret:string;classroom_id:string};
import {administrationCapabilities} from '../../domain/administration.ts';
export class ClassroomAdministration {
 private rpc:Rpc;
 constructor(rpc:Rpc){this.rpc=rpc;}
 async capabilities(room:string|null){return administrationCapabilities(await this.rpc('aire_admin_capabilities',{p_classroom_id:room}),room)}
 async revoke(gateway:{id:string;revision:number},reason:string){const note=reason.trim();if(!gateway.id||!Number.isInteger(gateway.revision)||note.length<3||note.length>500)throw Error('Indique un motivo de 3 a 500 caracteres.');const result=await this.rpc('aire_revoke_gateway',{p_gateway_id:gateway.id,p_revision:gateway.revision,p_reason:note});if(!result||result.id!==gateway.id||result.enabled!==false||!Number.isInteger(result.revision))throw Error('El retiro no pudo verificarse. Actualice el estado antes de reintentar.');return result}
 async create(name:string,school:string):Promise<string>{const title=name.trim();if(title.length<2||title.length>100||school.trim().length>120)throw Error('Revise nombre del aula e institución.');return this.rpc('aire_create_classroom',{p_name:title,p_school:school.trim()})}
 async assign(room:string,email:string,role:string){if(!room||!email.trim().includes('@')||!['admin','docente','observador'].includes(role))throw Error('Revise el aula, correo y rol.');return this.rpc('aire_grant_member',{p_classroom_id:room,p_email:email.trim(),p_role:role})}
 async pair(room:string,name:string){const title=name.trim();if(!room||title.length<2||title.length>100)throw Error('El nombre del receptor debe tener entre 2 y 100 caracteres.');const data=await this.rpc('aire_create_gateway',{p_classroom_id:room,p_name:title});if(!data||data.classroom_id!==room||typeof data.gateway_id!=='string'||typeof data.gateway_secret!=='string'||data.gateway_secret.length<40||data.gateway_secret.length>200)throw Error('El vínculo recibido no corresponde al aula o está incompleto. Revise el estado antes de generar otro.');return {gateway_id:data.gateway_id,gateway_secret:data.gateway_secret,classroom_id:data.classroom_id} as GatewayPair}
}
