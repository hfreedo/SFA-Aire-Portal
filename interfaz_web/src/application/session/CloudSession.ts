export type PublicConnection={url:string;key:string};
export type SessionSnapshot={configured:boolean;loading:boolean;actor:string|null;epoch:number;authBusy:boolean;preview:boolean;error:string};
export interface SessionPort {
 subscribe(listener:(actor:string|null)=>void):()=>void;
 restore():Promise<string|null>;
 signIn(email:string,password:string):Promise<string>;
 signOut():Promise<void>;
 rpc(name:string,args:Record<string,unknown>|undefined,actor:string):Promise<unknown>;
 local?(body:Record<string,unknown>,actor:string):Promise<unknown>;
 invoke?(name:string,body:Record<string,unknown>,actor:string):Promise<unknown>;
 dispose():void;
 clearLocal():void;
}
export type SessionPortFactory=(connection:PublicConnection)=>SessionPort;
export class SessionChanged extends Error {constructor(){super('La sesión cambió. Actualice el estado antes de continuar.')}}

/** Ciclo de vida único. No conoce React, componentes ni tipos internos de Supabase. */
export class CloudSession {
 private factory:SessionPortFactory;
 private clearConnection:(connection:PublicConnection)=>void;
 private retired:SessionPort|null=null;
 private connection:PublicConnection|null=null;
 private port:SessionPort|null=null;
 private unsubscribe:(()=>void)|null=null;
 private listeners=new Set<()=>void>();
 private operation=0;
 private disposed=false;
 private restoring:Promise<unknown>|null=null;
 private signingIn:Promise<unknown>|null=null;
 private signingOut:Promise<void>|null=null;
 private state:SessionSnapshot={configured:false,loading:true,actor:null,epoch:0,authBusy:false,preview:false,error:''};
 constructor(factory:SessionPortFactory,clearConnection:(connection:PublicConnection)=>void=()=>{}){this.factory=factory;this.clearConnection=clearConnection;}
 getSnapshot=()=>this.state;
 getConnection=()=>this.connection;
 subscribe=(listener:()=>void)=>{this.listeners.add(listener);return()=>{this.listeners.delete(listener)}};
 private update(patch:Partial<SessionSnapshot>){this.state={...this.state,...patch};for(const listener of [...this.listeners])listener()}
 private boundary(patch:Partial<SessionSnapshot>={}){this.update({actor:null,epoch:this.state.epoch+1,...patch})}
 private detach(){this.unsubscribe?.();this.unsubscribe=null;if(this.port){this.retired=this.port;this.port.dispose();}this.port=null;}
 private actor(value:string|null){if(value!==this.state.actor)this.update({actor:value,epoch:this.state.epoch+1})}
 configure(connection:PublicConnection|null,preview=false){
  this.disposed=false;this.operation++;this.detach();this.connection=connection;
  this.boundary({configured:!!connection,loading:false,authBusy:false,preview,error:''});
  if(connection&&!preview)this.activate(true);
 }
 failConfiguration(message:string){this.update({loading:false,error:message})}
 private activate(restore:boolean):SessionPort {
  if(this.port)return this.port;
  if(!this.connection)throw Error('La conexión institucional no está configurada.');
  const port=this.factory(this.connection);this.port=port;
  this.unsubscribe=port.subscribe(actor=>{if(!this.disposed&&this.port===port&&!this.state.preview)this.actor(actor)});
  if(restore){this.update({authBusy:true});const epoch=this.state.epoch;this.restoring=port.restore().then(actor=>{if(!this.disposed&&this.port===port&&epoch===this.state.epoch)this.actor(actor)}).catch(()=>{if(!this.disposed&&this.port===port&&epoch===this.state.epoch)this.update({error:'No se pudo recuperar la sesión. Puede volver a ingresar.'})}).finally(()=>{if(!this.disposed&&this.port===port)this.update({authBusy:false})});}
  return port;
 }
 async login(email:string,password:string){
  if(this.state.authBusy)throw Error('Hay una operación de acceso en curso.');
  const operation=++this.operation;this.boundary({authBusy:true,preview:false,error:''});
  try{const port=this.activate(false);const request=port.signIn(email.trim(),password);this.signingIn=request;const actor=await request;if(this.disposed||operation!==this.operation)throw new SessionChanged();this.actor(actor);}
  catch(error){if(operation===this.operation)this.actor(null);throw error;}
  finally{if(operation===this.operation&&!this.disposed)this.update({authBusy:false});}
 }
 enterPreview(){if(this.state.authBusy)throw Error('Espere a que termine la operación de acceso.');this.operation++;this.detach();this.boundary({preview:true,error:''})}
 logout():Promise<void>{
  if(this.signingOut)return this.signingOut;
  const operation=++this.operation,port=this.port||this.retired,waits=[this.signingIn,this.restoring].filter(Boolean);
  this.detach();this.boundary({authBusy:true,preview:false,error:''});
  const task=(async()=>{try{await Promise.allSettled(waits);if(port)await port.signOut();}catch{if(operation===this.operation)this.update({error:'Sesión cerrada en este navegador. No se pudo confirmar el cierre remoto.'})}finally{try{port?.clearLocal();if(!port&&this.connection)this.clearConnection(this.connection);}catch{if(operation===this.operation)this.update({error:'No se pudo retirar la sesión almacenada. Cierre esta pestaña antes de compartir el equipo.'})}finally{if(operation===this.operation&&!this.disposed)this.update({authBusy:false});if(this.retired===port)this.retired=null;this.signingOut=null;}}})();
  this.signingOut=task;return task;
 }
 async rpc<T=any>(name:string,args?:Record<string,unknown>):Promise<T>{
  const port=this.port,actor=this.state.actor,epoch=this.state.epoch;
  if(!port||!actor||this.state.preview||this.state.authBusy)throw Error('Primero verifique su sesión.');
  try{const result=await port.rpc(name,args,actor);if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();return result as T;}
  catch(error){if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();throw error;}
 }
 async local<T=any>(body:Record<string,unknown>):Promise<T>{
  const port=this.port,actor=this.state.actor,epoch=this.state.epoch;
  if(!port?.local||!actor||this.state.preview||this.state.authBusy)throw Error('Primero verifique su sesión.');
  try{const result=await port.local(body,actor);if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();return result as T;}
  catch(error){if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();throw error;}
 }
 async invoke<T=any>(name:string,body:Record<string,unknown>):Promise<T>{
  const port=this.port,actor=this.state.actor,epoch=this.state.epoch;
  if(!port?.invoke||!actor||this.state.preview||this.state.authBusy)throw Error('Primero verifique su sesión.');
  try{const result=await port.invoke(name,body,actor);if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();return result as T;}
  catch(error){if(this.disposed||port!==this.port||epoch!==this.state.epoch)throw new SessionChanged();throw error;}
 }
 dispose(){this.disposed=true;this.operation++;this.detach();this.listeners.clear();}
}
