import {useState} from 'react';
import {Bell,Share2} from 'lucide-react';
import type {CloudIncident,Overview} from '../../domain/models';
import {incidentAction,incidentInFilter} from '../../domain/monitoring';

type Props={incidents:CloudIncident[];deliveries:Overview['deliveries'];online:boolean;busy:boolean;demo:boolean;incidentFilter:string;onFilter:(filter:string)=>void;onAttention:(item:CloudIncident,action:string)=>void;onDirectAttention:(item:CloudIncident)=>void};
export default function IncidentsScreen({incidents,deliveries,online,busy,demo,incidentFilter,onFilter,onAttention,onDirectAttention}:Props){
 const [sharing,setSharing]=useState<string|null>(null),[feedback,setFeedback]=useState('');
 async function share(item:CloudIncident){
  const text='SFA Aire · '+(item.source==='simulacion'?'SIMULACIÓN':'Aviso ambiental')+' · '+new Date(item.opened_at).toLocaleString('es-PY')+'. '+(item.severity==='alerta'?'Revisar el ambiente del aula.':'Variación sostenida de la señal.')+' '+(item.note||'');
  setSharing(item.id);setFeedback('');
  try{if(navigator.share){await navigator.share({title:'Aviso SFA Aire',text});setFeedback('Se abrió el canal elegido. El envío y la respuesta se gestionan allí.')}else if(navigator.clipboard){await navigator.clipboard.writeText(text);setFeedback('Mensaje copiado. Puede pegarlo en el canal que prefiera.')}else setFeedback(text)}
  catch(error){if(!(error instanceof DOMException&&error.name==='AbortError'))setFeedback('No se pudo abrir el canal. Puede comunicar el aviso por su medio habitual.')}
  finally{setSharing(null)}
 }
 const visible=incidents.filter(i=>incidentInFilter(i,incidentFilter));
 return <section className="card"><div className="section-title"><h3>Avisos del aula</h3><span>{incidents.filter(i=>i.status!=='resuelto').length} pendientes</span></div>
 <div className="filter-tabs" role="group" aria-label="Filtrar avisos">{[['abiertos','Pendientes'],['resueltos','Atendidos'],['todos','Todos']].map(([id,label])=><button key={id} aria-pressed={incidentFilter===id} className={incidentFilter===id?'selected':'secondary'} onClick={()=>onFilter(id)}>{label}</button>)}</div>
 <p className="note">Revise el aviso y márquelo como atendido. Compartir o comentar es opcional.</p>
 {feedback&&<p role="status">{feedback}</p>}
 {!visible.length&&<div className="empty-state"><Bell size={30}/><h3>Sin avisos en esta vista</h3></div>}
 {visible.map(item=>{
  const close=incidentAction(item,'resolver',{online,demo,busy}),closed=item.status==='resuelto';
  const note=item.note?.replace(/^AVISO ATENDIDO · No confirma normalización del ambiente\.\s*/,'');
  return <article className={'incident '+(closed?'archived':item.severity)} key={item.id}><div><span className={'tag '+(item.source==='simulacion'?'simulation':'')}>{item.source==='simulacion'?'SIMULACIÓN':'ARDUINO'}</span><h3>{closed?'Aviso atendido':item.severity==='alerta'?'Revisar aula':'Variación sostenida'}</h3>
   <p>{new Date(item.opened_at).toLocaleString('es-PY')}{item.historical?' · Registro histórico':''}</p>
   {note&&<p>{note}</p>}
   {closed&&<small>La atención de este aviso no confirma normalización del ambiente. Consulte la medición actual en Mis aulas.</small>}
   <p><small>Notificaciones: {deliveries.filter(d=>d.incident_id===item.id).map(d=>d.status.replaceAll('_',' ')).join(' · ')||'Sin entregas registradas'}</small></p>
  </div><div className="incident-decisions"><div className="actions">
   {!closed&&<button disabled={!demo&&!close.allowed} onClick={()=>demo?onAttention(item,'resolver'):onDirectAttention(item)}>Marcar atendido</button>}
   <button className="secondary" disabled={sharing!==null} onClick={()=>void share(item)}><Share2 size={16}/>Compartir aviso</button>
   {!closed&&<button className="text-button" disabled={!demo&&!close.allowed} onClick={()=>onAttention(item,'resolver')}>Atender con comentario</button>}
  </div>{!closed&&!demo&&!close.allowed&&<p>{close.reason}</p>}</div></article>
 })}</section>;
}
