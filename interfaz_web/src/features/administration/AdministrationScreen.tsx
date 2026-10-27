import {useCallback,useEffect,useLayoutEffect,useMemo,useRef,useState} from 'react';
import {Download,Plus,School,Users,Monitor,Unplug,Pencil,RefreshCw} from 'lucide-react';
import './administration.css';
import {ClassroomAdministration,type Rpc} from '../../application/workspace/ClassroomAdministration';
import {ResultScope} from '../../application/workspace/ResultScope';
import type {Gateway} from '../../domain/administration';
import type {AdministrationState} from './useAdministrationCapabilities';
import ReasonDialog from '../../shared/dialogs/ReasonDialog';
import ClassroomEditor from './ClassroomEditor';
import PersonEditor from './PersonEditor';
import InvitationsList from './InvitationsList';
import ConfirmAccessRemoval from './ConfirmAccessRemoval';
type Room={id:string;name:string;school:string};
type Member={id:string;email:string;role:string;owner:boolean;current:boolean;phone_count:number;last_registered_at:string|null;last_received_at:string|null};
type Detail={classroom:Room&{revision:number};can_edit:boolean;can_manage_members:boolean;members:Member[];member_limit:number;account_creation_available:boolean};
type Props={room:string;rooms:Room[];onArduino:()=>void;onSelect:(id:string)=>void;demo:boolean;online:boolean;connection:{url:string;key:string};contextKey:string;capabilities:AdministrationState;reloadCapabilities:()=>Promise<void>;rpc:Rpc;invoke:(name:string,body:Record<string,unknown>)=>Promise<any>;onChanged:()=>Promise<void>;onCreated:(id:string)=>void};
const roleLabel:Record<string,string>={admin:'Administrador',docente:'Docente',observador:'Observador'};
export default function AdministrationScreen({room,rooms,onArduino,onSelect,demo,online,connection,contextKey,capabilities,reloadCapabilities,rpc,invoke,onChanged,onCreated}:Props){
 const actions=useMemo(()=>new ClassroomAdministration(rpc),[rpc]);
 const [scope]=useState(()=>new ResultScope());scope.select(contextKey+':'+online+':'+demo);
 const pending=useRef(false),request=useRef(0),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[detail,setDetail]=useState<Detail|null>(null),[detailError,setDetailError]=useState(''),[loading,setLoading]=useState(false);
 const [invitesVersion,setInvitesVersion]=useState(0);
 const [tab,setTab]=useState('aulas'),[editor,setEditor]=useState<'new'|'edit'|null>(null),[person,setPerson]=useState<Member|'new'|null>(null),[removing,setRemoving]=useState<Member|null>(null),[pairForm,setPairForm]=useState(false),[gatewayName,setGatewayName]=useState('PC que tiene el Arduino'),[pairing,setPairing]=useState<Record<string,string>|null>(null),[retiring,setRetiring]=useState<Gateway|null>(null);
 useLayoutEffect(()=>{scope.activate();return()=>scope.dispose()},[scope]);
 const caps=capabilities.data,verified=online&&!demo&&capabilities.ready,selected=rooms.find(r=>r.id===room);
 const canCreate=verified&&caps?.can_create_classroom===true,canMembers=verified&&detail?.can_manage_members===true&&caps?.can_manage_members===true,canGateways=verified&&caps?.can_manage_gateways===true;
 const atLimit=!!caps&&caps.active_gateways>=caps.gateway_limit;
 const reloadDetail=useCallback(async()=>{
  if(!room||!online||demo){setDetail(null);return}
  const ticket=scope.capture(),version=++request.current;setLoading(true);
  try{const value=await rpc('aire_classroom_admin',{p_classroom_id:room});
   if(!scope.accepts(ticket)||version!==request.current)return;
   if(value?.classroom?.id!==room||typeof value.can_edit!=='boolean'||typeof value.can_manage_members!=='boolean'||!Array.isArray(value.members)||value.members.length>100||!Number.isInteger(value.classroom.revision)||!Number.isInteger(value.member_limit)||typeof value.account_creation_available!=='boolean'||value.members.some((m:any)=>typeof m.id!=='string'||typeof m.email!=='string'||!['admin','docente','observador'].includes(m.role)||!Number.isInteger(m.phone_count)||typeof m.owner!=='boolean'||typeof m.current!=='boolean'))throw Error('No se pudo verificar el detalle del aula. Actualice para volver a intentar.');
   setDetail(value);setDetailError('');
  }catch(e){if(scope.accepts(ticket)&&version===request.current){setDetail(null);setDetailError(e instanceof Error?e.message:String(e))}}
  finally{if(scope.accepts(ticket)&&version===request.current)setLoading(false)}
 },[room,online,demo,rpc,scope]);
 useEffect(()=>{void reloadDetail()},[reloadDetail]);
 useEffect(()=>{if(demo||!online||caps?.can_manage_gateways===false){setPairing(null);setRetiring(null)}},[demo,online,caps?.can_manage_gateways]);
 async function run<T,>(allowed:boolean,action:()=>Promise<T>,apply?:(value:T)=>void){
  if(!allowed||pending.current)throw Error('No hay permisos o conexión vigentes para guardar.');
  pending.current=true;setBusy(true);setNotice('');const ticket=scope.capture();
  try{const value=await action();if(!scope.accepts(ticket))throw Error('Cambió el aula o la sesión. Revise su selección.');apply?.(value);setNotice('Cambio guardado.');await Promise.all([onChanged(),reloadCapabilities(),reloadDetail()]);return value}
  catch(e){if(scope.accepts(ticket))setNotice(e instanceof Error?e.message:String(e));throw e}
  finally{pending.current=false;if(scope.accepts(ticket))setBusy(false)}
 }
 function download(){if(!pairing||!canGateways)return;const blob=new Blob([JSON.stringify(pairing,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='supabase-pc.json';link.click();setPairing(null);setTimeout(()=>URL.revokeObjectURL(url),1000)}
 function changeTab(next:string){setPairing(null);setRetiring(null);setPairForm(false);setTab(next);setNotice('')}
 return <div className="administration-workspace">
 {notice&&<div className="notice" role="status">{notice}</div>}
 {demo&&<div className="banner">Demostración: las aulas mostradas son ejemplos. La gestión de cuentas y PC requiere iniciar sesión.</div>}
 <div className="admin-toolbar"><div><h1>Administración de aulas</h1><p>Selecciona un aula y revisa sus personas y su PC.</p></div><button className="secondary" disabled={!online||demo||busy||loading} onClick={()=>{void onChanged();void reloadDetail();void reloadCapabilities()}}><RefreshCw size={16}/>Actualizar configuración</button></div>
 <div className="admin-workspace-grid"><section className="card classroom-directory"><div className="section-title"><h3>Aulas</h3><span>{rooms.length}</span></div>
 <button className="secondary" disabled={!canCreate||busy} onClick={()=>setEditor('new')}><Plus size={16}/>Nueva aula</button>
 {!canCreate&&!demo&&caps?.create_reason&&<small>{caps.create_reason}</small>}
 <div className="classroom-choices">{rooms.map(r=><button key={r.id} className={'classroom-choice '+(r.id===room?'active':'')} aria-pressed={r.id===room} disabled={busy} onClick={()=>onSelect(r.id)}><School size={18}/><span><b>{r.name}</b><small>{r.school||'Institución sin indicar'}</small></span></button>)}</div>
 {!rooms.length&&<p>No hay aulas registradas. Usa Nueva aula para empezar.</p>}</section>
 <div className="classroom-detail">{selected?<><section className="card classroom-summary"><div><span className="eyebrow">AULA SELECCIONADA</span><h2>{selected.name}</h2><p>{selected.school||'Puedes indicar la institución al editar el aula.'}</p></div><button className="secondary" disabled={!verified||!detail?.can_edit||busy} onClick={()=>setEditor('edit')}><Pencil size={15}/>Editar datos</button></section>
 <nav className="admin-tabs" aria-label="Configuración del aula">{[{id:'aulas',label:'Resumen',icon:School},{id:'personas',label:'Personas',icon:Users},{id:'pc',label:'PC del aula',icon:Monitor}].map(({id,label,icon:Icon})=><button key={id} disabled={busy} aria-current={tab===id?'page':undefined} className={tab===id?'selected':'secondary'} onClick={()=>changeTab(id)}><Icon size={16}/>{label}</button>)}</nav>
 {detailError&&<div className="banner error" role="alert">{detailError}</div>}
 {loading&&!detail&&<p role="status">Cargando personas y configuración del aula…</p>}
 {tab==='aulas'&&<section className="card classroom-overview"><h3>Configuración de {selected.name}</h3><div className="setup-summary"><article><Users size={21}/><div><b>{detail?detail.members.length:'—'} {detail?.members.length===1?'persona':'personas'} con acceso</b><p>Consulta quién puede ingresar y sus teléfonos registrados.</p></div><button className="secondary" onClick={()=>changeTab('personas')}>Ver personas</button></article><article><Monitor size={21}/><div><b>{caps?caps.active_gateways:'—'} {caps?.active_gateways===1?'PC registrada':'PC registradas'}</b><p>{caps?.gateways.some(g=>g.enabled&&g.paired)?'Hay una PC vinculada al aula.':'Todavía no hay una PC vinculada que envíe mediciones.'}</p></div><button className="secondary" onClick={()=>changeTab('pc')}>Ver PC del aula</button></article></div><div className="admin-explanation"><b>¿Qué se configura aquí?</b><p>El aula reúne las mediciones y los avisos. Las personas ingresan con su propia cuenta. La PC conectada al Arduino envía las mediciones; los celulares se registran desde la app de cada persona.</p></div></section>}
 {tab==='personas'&&<section className="card"><div className="section-title"><h3>Personas de {selected.name}</h3><button disabled={!canMembers||busy||!detail||detail.members.length>=detail.member_limit} onClick={()=>setPerson('new')}><Plus size={16}/>Agregar persona</button></div><p>{detail?detail.members.length+' / '+detail.member_limit+' personas registradas. ':''}Las personas registran su celular desde Ajustes en Android. No se agregan como PC del aula.</p>{detail&&detail.members.length>=detail.member_limit&&<p className="permission-reason">Llegaste al límite preventivo de personas del aula. Revisa los accesos que ya no se utilicen.</p>}
 <div className="people-list">{detail?.members.map(m=><article key={m.id} className="person-row"><div className="person-avatar" aria-hidden="true">{m.email[0]?.toUpperCase()}</div><div className="person-info"><b>{m.email}</b><p>{roleLabel[m.role]}{m.current?' · Tú':''}{m.owner?' · Propietario del aula':''}</p><small>{m.phone_count?m.phone_count+(m.phone_count===1?' teléfono registrado':' teléfonos registrados'):'Sin teléfono registrado'}{m.last_received_at?' · Último acuse: '+new Date(m.last_received_at).toLocaleString('es-PY'):''}</small></div>{!m.owner&&!m.current&&<div className="actions"><button className="secondary" disabled={!canMembers||busy} onClick={()=>setPerson(m)}>Editar acceso</button><button className="secondary" disabled={!canMembers||busy} onClick={()=>setRemoving(m)}>Retirar acceso</button></div>}</article>)}</div>
 {!detail&&!loading&&<div className="empty-state">Actualiza la configuración para ver las personas autorizadas.</div>}</section>}
 {tab==='personas'&&<InvitationsList room={room} rpc={rpc} refresh={invitesVersion} enabled={canMembers}/>}
 {tab==='pc'&&<section className="card"><div className="section-title"><h3>PC que envían datos a {selected.name}</h3><span>{caps?.active_gateways??'—'} / {caps?.gateway_limit??'—'} PC registradas</span></div><button className="secondary" disabled={!canGateways||busy} onClick={onArduino}>Conectar Arduino en esta PC</button><div className="admin-explanation"><b>Una PC receptora no es un celular</b><p>Registra aquí el equipo al que conectas el Arduino por USB. Para agregar un docente o su celular, usa Personas y la app Android.</p></div>
 <ul className="gateway-list">{caps?.gateways.map(g=><li key={g.id}><div><b>{g.name}</b><span className={'tag '+(!g.enabled?'gateway-retired':'')}>{!g.enabled?'Acceso retirado':g.paired?'PC vinculada':'Sin conectar a una PC'}</span><p>{g.last_seen_at?'Último contacto: '+new Date(g.last_seen_at).toLocaleString('es-PY'):g.enabled?'Se creó la credencial, pero esta PC aún no ha enviado datos.':'El historial se conserva.'}</p>{g.revoked_reason&&<small>Motivo: {g.revoked_reason}</small>}</div>{g.enabled&&<button className="secondary" disabled={!canGateways||busy} onClick={()=>setRetiring(g)}><Unplug size={15}/>Retirar PC</button>}</li>)}</ul>
 {atLimit&&<p className="permission-reason">Ya hay {caps?.gateway_limit} PC registradas para esta aula. Revisa las PC anteriores antes de registrar otra; no necesitas una credencial por celular.</p>}
 {!pairForm?<button disabled={!canGateways||atLimit||busy} onClick={()=>setPairForm(true)}><Plus size={16}/>Registrar PC con Arduino</button>:<form className="gateway-create" onSubmit={e=>{e.preventDefault();void run(canGateways&&!atLimit,()=>actions.pair(room,gatewayName),info=>setPairing({url:connection.url,publishable_key:connection.key,...info})).catch(()=>{})}}><label>Nombre de la PC<input required minLength={2} maxLength={100} value={gatewayName} onChange={e=>setGatewayName(e.target.value)}/></label><div className="actions"><button disabled={!canGateways||atLimit||busy}>Crear vínculo de PC</button><button type="button" className="secondary" disabled={busy} onClick={()=>setPairForm(false)}>Cancelar</button></div></form>}
 {pairing&&canGateways&&<div className="pairing"><p>Esta configuración identifica la PC de esta aula. Guárdala de forma privada como secrets/supabase-pc.json en el receptor.</p><button className="secondary" onClick={download}><Download size={15}/>Descargar configuración PC</button><button className="secondary" onClick={()=>setPairing(null)}>Ocultar</button></div>}</section>}
 </>:<section className="card empty-state"><School size={32}/><h3>Empieza por registrar un aula</h3><p>Después podrás agregar sus personas y vincular la PC del Arduino.</p></section>}</div></div>
 {editor&&<ClassroomEditor initial={editor==='edit'?selected:undefined} onClose={()=>setEditor(null)} onSave={async(name,school)=>{if(editor==='new')await run(canCreate,()=>actions.create(name,school),id=>onCreated(id));else await run(verified&&!!detail?.can_edit,()=>rpc('aire_update_classroom',{p_classroom_id:room,p_revision:detail?.classroom.revision,p_name:name,p_school:school}))}}/>}
 {person&&<PersonEditor canCreate={detail?.account_creation_available===true} initial={person==='new'?undefined:person} onClose={()=>setPerson(null)} onInvite={async(email,role)=>{const value=await run(canMembers,()=>invoke('aire-invitations',{classroom_id:room,email,role}));setInvitesVersion(v=>v+1);return value}} onSave={async(email,role)=>{await run(canMembers,()=>invoke('aire-members',{classroom_id:room,email,role}));}}/>}
 {removing&&<ConfirmAccessRemoval email={removing.email} onClose={()=>setRemoving(null)} onSave={async()=>{await run(canMembers,()=>rpc('aire_remove_member',{p_classroom_id:room,p_user_id:removing.id}))}}/>}
 {retiring&&<ReasonDialog title="Retirar acceso de la PC" description="Esta PC dejará de enviar datos al aula. Las cuentas de las personas no se eliminan." warning="Se invalida la credencial de este equipo. Conserva el historial del aula." context={retiring.name} label="Motivo del retiro" confirmLabel="Retirar PC" allowed={canGateways} onClose={()=>setRetiring(null)} onSave={async reason=>{await run(canGateways,()=>actions.revoke(retiring,reason))}}/>}
 </div>;
}
