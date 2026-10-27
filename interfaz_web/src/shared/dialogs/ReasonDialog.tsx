import {useEffect,useLayoutEffect,useRef,useState} from 'react';
import {X,ClipboardCheck} from 'lucide-react';
type Props={title:string;description:string;warning:string;context:string;label:string;confirmLabel:string;allowed:boolean;demo?:boolean;onClose:()=>void;onSave:(reason:string)=>Promise<void>};
/** Formulario común para decisiones con motivo; no ejecuta RPC ni decide permisos. */
export default function ReasonDialog({title,description,warning,context,label,confirmLabel,allowed,demo=false,onClose,onSave}:Props){
 const ref=useRef<HTMLDialogElement>(null),live=useRef(true),[reason,setReason]=useState(''),[saving,setSaving]=useState(false),[error,setError]=useState('');
 useLayoutEffect(()=>{live.current=true;return()=>{live.current=false}},[]);
 useEffect(()=>{ref.current?.showModal();return()=>ref.current?.close()},[]);
 async function submit(event:React.FormEvent){event.preventDefault();if(!allowed||demo||saving||reason.trim().length<3)return;setSaving(true);setError('');try{await onSave(reason.trim());if(live.current)onClose()}catch(error){if(live.current)setError(error instanceof Error?error.message:String(error))}finally{if(live.current)setSaving(false)}}
 return <dialog ref={ref} className="attention-dialog" aria-labelledby="reason-title" aria-describedby="reason-description" onCancel={event=>{event.preventDefault();if(!saving)onClose()}}><form onSubmit={submit}>
  <div className="dialog-heading"><span className="dialog-icon"><ClipboardCheck aria-hidden="true"/></span><button type="button" className="icon-button secondary" aria-label="Cerrar formulario" disabled={saving} onClick={onClose}><X size={19} aria-hidden="true"/></button></div>
  <h2 id="reason-title">{title}</h2><p id="reason-description">{description}</p><div className="dialog-context">{context}</div><div className="banner simulation">{warning}</div>
  {demo&&<div className="banner demo-banner">Demostración ficticia. No se guardan cambios ni se envían avisos.</div>}
  {!allowed&&!demo&&<div className="banner error">Acción sin verificar. Revise el estado y sus capacidades antes de continuar.</div>}
  <label htmlFor="decision-reason">{label}</label><textarea id="decision-reason" required minLength={3} maxLength={500} rows={5} value={reason} autoFocus disabled={saving} aria-describedby="decision-help" onChange={event=>setReason(event.target.value)}/><div className="field-help" id="decision-help"><span>Mínimo 3 caracteres. El motivo queda en la traza.</span><span>{reason.length}/500</span></div>
  {error&&<div className="banner error" role="alert">{error}<p>El motivo se conserva. Revise el rechazo antes de reintentar.</p></div>}
  <div className="dialog-actions"><button type="button" className="secondary" disabled={saving} onClick={onClose}>Cancelar</button><button disabled={!allowed||demo||saving||reason.trim().length<3}>{saving?'Guardando…':confirmLabel}</button></div>
 </form></dialog>;
}
