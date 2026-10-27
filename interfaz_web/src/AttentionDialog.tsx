import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {X,ClipboardCheck,ShieldCheck} from 'lucide-react';
export type AttentionTarget={id:string;action:string;source:string;opened:string;status:string;note?:string;revision?:number};
type Props={target:AttentionTarget;room:string;allowed:boolean;demo?:boolean;onClose:()=>void;onSave:(note:string)=>Promise<void>};
export default function AttentionDialog({target,room,allowed,demo,onClose,onSave}:Props){
 const ref=useRef<HTMLDialogElement>(null),[note,setNote]=useState(''),[saving,setSaving]=useState(false),[error,setError]=useState('');
 const mounted=useRef(true);useLayoutEffect(()=>{mounted.current=true;return()=>{mounted.current=false}},[]);
 const resolving=target.action==='resolver';
 useEffect(()=>{const dialog=ref.current;dialog?.showModal();return()=>{dialog?.close()}},[]);
 async function submit(e:React.FormEvent){e.preventDefault();if(!allowed||saving)return;setSaving(true);setError('');try{await onSave(note.trim());if(mounted.current)onClose()}catch(e){if(mounted.current)setError(e instanceof Error?e.message:String(e))}finally{if(mounted.current)setSaving(false)}}
 return <dialog ref={ref} className="attention-dialog" aria-labelledby="attention-title" aria-describedby="attention-explanation" onCancel={e=>{e.preventDefault();if(!saving)onClose()}}>
 <form onSubmit={submit}><div className="dialog-heading"><span className="dialog-icon">{resolving?<ShieldCheck/>:<ClipboardCheck/>}</span><button type="button" className="icon-button secondary" aria-label="Cerrar formulario" disabled={saving} onClick={onClose}><X size={19}/></button></div>
 <p className="eyebrow">{target.source==='simulacion'?'SIMULACIÓN':'ARDUINO'} · {room}</p><h2 id="attention-title">{resolving?'Marcar aviso como atendido':'Revisar aviso'}</h2>
 <p id="attention-explanation">{resolving?'El aviso dejará de estar pendiente. Esto no cambia la medición ni confirma que el ambiente se haya normalizado.':'Puede dejar una nota si le resulta útil. No necesita completar indicaciones ni contactar a otra persona.'}</p>
 <div className="dialog-context"><span>Abierto el {target.opened}</span><b>{target.status.replaceAll('_',' ')}</b>{target.note&&<p>Último registro: {target.note}</p>}</div>
 {demo&&<div className="banner demo-banner">Vista de demostración. Puede explorar el formulario; no se guardan cambios ni se envían avisos.</div>}
 {!allowed&&!demo&&<div className="banner error">No hay conexión o permisos vigentes para guardar. Puede conservar esta nota y volver a verificar el estado.</div>}
 <label htmlFor="attention-note">Nota opcional</label><textarea id="attention-note" aria-describedby="attention-help" maxLength={500} rows={3} value={note} disabled={saving} onChange={e=>setNote(e.target.value)} placeholder={resolving?'Añada un comentario si lo desea…':'Qué observó y qué acción tomó…'}/>
 <div className="field-help" id="attention-help"><span>Puede guardar sin escribir. La atención queda registrada con su cuenta.</span><span>{note.length}/500</span></div>
 {error&&<div className="banner error" role="alert">{error}<p>La nota se conserva. Revise el motivo antes de intentar nuevamente.</p></div>}
 <div className="dialog-actions"><button type="button" className="secondary" disabled={saving} onClick={onClose}>Cancelar</button><button disabled={!allowed||saving}>{saving?'Guardando…':resolving?'Marcar atendido':'Guardar atención'}</button></div>
 </form></dialog>
}
