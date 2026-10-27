export type ScopeTicket={key:string;version:number};
/** Descarta resultados de contextos abandonados; no revierte comandos ya enviados. */
export class ResultScope {
 private key='';private version=0;private alive=true;
 select(key:string){if(key!==this.key){this.key=key;this.version++}}
 activate(){if(!this.alive){this.alive=true;this.version++}}
 capture():ScopeTicket{return {key:this.key,version:this.version}}
 accepts(ticket:ScopeTicket){return this.alive&&ticket.key===this.key&&ticket.version===this.version}
 dispose(){this.alive=false;this.version++}
}
