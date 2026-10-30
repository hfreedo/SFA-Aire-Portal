import StyledSelect from './shared/StyledSelect';
import PortalBoundary from './shared/PortalBoundary';
import {lazy,Suspense,useCallback,useEffect,useLayoutEffect,useRef,useState} from 'react';
import {useInstitutionSession} from './features/access/useInstitutionSession';
import {hostedPortal} from './data/cloud/publicConnection';
import {Bell,RefreshCw} from 'lucide-react';
import LoginScreen from './features/access/LoginScreen';
import ClassroomScreen from './features/monitoring/ClassroomScreen';
import {useLocalObservation} from './features/monitoring/useLocalObservation';
import IncidentsScreen from './features/incidents/IncidentsScreen';
import HistoryScreen from './features/history/HistoryScreen';
import AdministrationScreen from './features/administration/AdministrationScreen';
import {ResultScope} from './application/workspace/ResultScope';
import {exampleOverview} from './data/demo/overview';
import type {Overview,CloudIncident} from './domain/models';
import './cloud.css';
import './portal-theme.css';
import './scroll-surfaces.css';
const ArduinoScreen=lazy(()=>import('./features/arduino/ArduinoScreen'));
const AdminLab=lazy(()=>import('./AdminLab'));

import WorkspaceSidebar from './shared/layout/WorkspaceSidebar';
import AttentionDialog,{type AttentionTarget} from './AttentionDialog';

import {incidentAction,type IncidentAction} from './domain/monitoring';
import {useAdministrationCapabilities} from './features/administration/useAdministrationCapabilities';
function readableError(error:unknown){const message=error instanceof Error?error.message:String(error);if(/invalid login credentials/i.test(message))return 'El correo o la contraseña no coinciden. Revise los datos e intente nuevamente.';if(/failed to fetch|networkerror|network request failed/i.test(message))return 'No se pudo conectar. Compruebe su red y vuelva a intentar.';if(/email not confirmed/i.test(message))return 'La cuenta necesita confirmar su correo antes de ingresar.';return message;}
const requestedDemo=new URLSearchParams(location.search).get('demo')==='1';
export default function RemoteWorkspace(){
 const {state:session,service}=useInstitutionSession(requestedDemo);
 const config=service.getConnection(),url=config?.url||'',publicKey=config?.key||'';
 const signed=!!session.actor;
 const [demo,setDemo]=useState(requestedDemo),[viewState,setViewState]=useState<{data:Overview;epoch:number;demo:boolean}|null>(null),[room,setRoom]=useState(''),[online,setOnline]=useState(false),[notice,setNotice]=useState(''),[refreshError,setRefreshError]=useState(''),[operationBusy,setBusy]=useState(false),[page,setPage]=useState('aulas');
 const view=viewState&&(demo&&viewState.demo||!demo&&!viewState.demo&&viewState.epoch===session.epoch)?viewState.data:null;
 const [overviewLoading,setOverviewLoading]=useState(true);
 const busy=operationBusy||session.authBusy;
 function setView(data:Overview|null,isDemo=false){setViewState(data?{data,epoch:service.getSnapshot().epoch,demo:isDemo}:null)}
 const [readings,setReadings]=useState<{sample_at:string;state:string;observation:{mq_raw:number;ratio:number|null}}[]>([]),[source,setSource]=useState('arduino');
 const [resultScope]=useState(()=>new ResultScope());resultScope.select(`${session.epoch}:${room}:${source}:${page}`);
 useLayoutEffect(()=>{resultScope.activate();return()=>resultScope.dispose()},[resultScope]);
 const [clock,setClock]=useState(Date.now());
 const launchHandled=useRef(false);
 const generation=useRef(session.epoch);generation.current=session.epoch;const overviewRequest=useRef(0);
 const [attentionTarget,setAttentionTarget]=useState<AttentionTarget|null>(null),[incidentFilter,setIncidentFilter]=useState('abiertos');
 useEffect(()=>{if(requestedDemo){const example=exampleOverview();example.memberships=example.memberships.map(m=>({...m,role:'admin'}));setDemo(true);setView(example,true);setRoom(example.classrooms[0].id);setOnline(false);setPage('aulas')}},[]);
 useEffect(()=>{const t=setInterval(()=>setClock(Date.now()),2000);return()=>clearInterval(t)},[]);
 useEffect(()=>{setAttentionTarget(null);setReadings([]);setOnline(false);setRefreshError('');setBusy(false);if(!session.actor&&!demo){setView(null);setRoom('');setPage('aulas')}},[session.epoch]);
 const rpc=useCallback((name:string,args?:Record<string,unknown>)=>service.rpc(name,args),[service]);
 const local=useCallback((body:Record<string,unknown>)=>service.local(body),[service]);
 const administration=useAdministrationCapabilities(rpc,room,`${session.epoch}:${room}`,signed&&!session.authBusy&&!demo&&online);
 async function refresh(){if(demo)return;const request=generation.current,version=++overviewRequest.current;setOverviewLoading(true);try{const data=await rpc('aire_overview');if(request!==generation.current||version!==overviewRequest.current)return;setView(data);setOnline(true);setRefreshError('');let remembered='';try{remembered=sessionStorage.getItem('sfa-room:'+session.actor)||''}catch{}setRoom(old=>data.classrooms.some((c:{id:string})=>c.id===old)?old:data.classrooms.some((c:{id:string})=>c.id===remembered)?remembered:data.classrooms[0]?.id||'')}catch(e){if(request===generation.current&&version===overviewRequest.current){setOnline(false);setRefreshError(readableError(e))}}finally{if(request===generation.current&&version===overviewRequest.current)setOverviewLoading(false)}}
 useEffect(()=>{if(!signed||session.authBusy||demo)return;void refresh();const t=setInterval(()=>{if(document.visibilityState==='visible')void refresh()},60000);return()=>clearInterval(t)},[signed,session.epoch,session.authBusy,demo]);
 async function login(email:string,password:string){try{await service.login(email,password);setDemo(false);setNotice('');return true;}catch(error){setNotice(readableError(error));return false;}}
 function startDemo(page:string){if(session.authBusy)return;service.enterPreview();const example=exampleOverview();if(page==='laboratorio')example.memberships=example.memberships.map(m=>({...m,role:'admin'}));setDemo(true);setView(example,true);setRoom(example.classrooms[0].id);setOnline(false);setNotice('');setPage(page)}
 function logout(){void service.logout();setDemo(false);setView(null);setOnline(false);setRoom('');setAttentionTarget(null);setReadings([]);setPage('aulas');setNotice('')}
 function attention(item:CloudIncident,action:string){setAttentionTarget({id:item.id,action,source:item.source,opened:new Date(item.opened_at).toLocaleString('es-PY'),status:item.status,note:item.note,revision:item.revision})}
 const directPending=useRef(false);
 async function attendDirect(item:CloudIncident){
  const allowed=incidentAction(item,'resolver',{online,demo,busy});if(!allowed.allowed||directPending.current){if(!allowed.allowed)setNotice(allowed.reason);return}
  const ticket=resultScope.capture();directPending.current=true;setBusy(true);setNotice('');
  try{await rpc('aire_attention',{p_incident_id:item.id,p_revision:item.revision,p_action:'resolver',p_note:''});if(resultScope.accepts(ticket)){setIncidentFilter('resueltos');await refresh();if(resultScope.accepts(ticket))setNotice('Aviso marcado como atendido. La medición ambiental sigue siendo independiente.')}}
  catch(error){if(resultScope.accepts(ticket))setNotice(readableError(error))}
  finally{directPending.current=false;if(resultScope.accepts(ticket))setBusy(false)}
 }
 function navigate(id:string){setBusy(false);setPage(id);setReadings([]);setAttentionTarget(null)}
 async function saveAttention(note:string){
  const ticket=resultScope.capture(),target=attentionTarget,item=incidents.find(i=>i.id===target?.id);
  if(!item||!target)throw Error('El incidente ya no está disponible. Actualice el estado.');
  const availability=incidentAction(item,target.action as IncidentAction,{online,demo,busy});
  if(!availability.allowed)throw Error(availability.reason);
  if(item.revision!==target.revision)throw Error('El incidente cambió mientras completaba el formulario. Cancele y revise el estado actualizado.');
  await rpc('aire_attention',{p_incident_id:item.id,p_revision:target.revision,p_action:target.action,p_note:note});
  if(!resultScope.accepts(ticket))throw Error('El contexto cambió. Revise el incidente en su aula actual.');
  setNotice(target.action==='resolver'?'Aviso marcado como atendido. La medición ambiental sigue siendo independiente.':'Atención registrada. El incidente continúa abierto.');await refresh();
 }
 async function history(){if(busy||demo||!online)return;const ticket=resultScope.capture();setBusy(true);try{const data=await rpc('aire_history',{p_classroom_id:room,p_source:source});if(resultScope.accepts(ticket))setReadings(data.readings)}catch(error){if(resultScope.accepts(ticket))setNotice(readableError(error))}finally{if(resultScope.accepts(ticket))setBusy(false)}}
 const rooms=view?.classrooms||[],selected=rooms.find(c=>c.id===room),myRole=view?.memberships.find(m=>m.classroom_id===room)?.role;
 useEffect(()=>{const target=new URLSearchParams(location.search).get('view');if(!launchHandled.current&&view&&signed&&!demo&&myRole==='admin'&&['arduino','gestion','laboratorio'].includes(target||'')){launchHandled.current=true;navigate(target!)}},[view,signed,demo,myRole]);
 useEffect(()=>{if(session.actor&&!demo&&view?.classrooms.some(c=>c.id===room)){try{sessionStorage.setItem('sfa-room:'+session.actor,room)}catch{}}},[room,session.actor,demo,view]);
 const incidents=view?.incidents.filter(i=>i.classroom_id===room)||[],snapshots=view?.snapshots.filter(s=>s.classroom_id===room)||[];
 const canAdminister=myRole==='admin'||administration.state.data?.can_create_classroom===true;
 useEffect(()=>{if(view&&((page==='laboratorio'||page==='arduino')&&myRole!=='admin'||page==='gestion'&&!canAdminister&&!administration.state.loading))navigate('aulas')},[view,page,myRole,canAdminister,administration.state.loading]);
 const liveObservation=useLocalObservation(room,`${session.epoch}:${room}`,signed&&!session.authBusy&&!demo&&!hostedPortal&&myRole==='admin'&&page==='aulas',local);
 useEffect(()=>{if(!liveObservation?.snapshot.observation.usb_cloud||!signed||demo)return;void refresh();const timer=setInterval(()=>{if(document.visibilityState==='visible')void refresh()},10000);return()=>clearInterval(timer)},[!!liveObservation?.snapshot.observation.usb_cloud,signed,demo,room]);
 const targetIncident=incidents.find(i=>i.id===attentionTarget?.id);
 const canSaveAttention=!!targetIncident&&!!attentionTarget&&incidentAction(targetIncident,attentionTarget.action as IncidentAction,{online,demo,busy}).allowed;
 if(!signed&&!demo)return <LoginScreen configured={!!url&&!!publicKey} loading={session.loading} busy={busy} notice={notice||session.error} onLogin={login} onExplore={startDemo}/>;
 if(signed&&!demo&&!view)return <div className="shell cloud-shell portal-theme"><WorkspaceSidebar mode="cloud" page="aulas" online={false} connectionLabel={overviewLoading?'Consultando aulas…':'Sin verificar'} onNavigate={()=>{}} onLogout={logout}/><main><section className="card workspace-status" role="status"><h1>{overviewLoading?'Cargando tus aulas…':'No se pudo cargar el monitoreo'}</h1><p>{overviewLoading?'Comprobando la sesión y el estado del monitoreo.':'Necesitamos verificar la conexión y tu sesión antes de mostrar aulas, mediciones o avisos.'}</p>{!overviewLoading&&<><p className="workspace-status-detail">{refreshError||notice||'Comprueba la conexión y vuelve a intentar.'}</p><div className="actions"><button disabled={busy} onClick={()=>void refresh()}>Volver a intentar</button><button className="secondary" disabled={busy} onClick={logout}>Volver a ingresar</button></div></>}</section></main></div>;
 return <div className="shell cloud-shell portal-theme"><WorkspaceSidebar mode="cloud" page={page} role={myRole} canAdminister={canAdminister} online={online} connectionLabel={demo?'Demostración':online?'Nube conectada':'Sin conexión'} onNavigate={navigate} onLogout={logout}/><main>
 {page!=='gestion'&&<header><div><h1>{page==='arduino'?'Conexión Arduino':page==='laboratorio'?'Pruebas de integración':page==='gestion'?'Personas y aulas':page==='incidentes'?'Avisos del aula':page==='historial'?'La evolución del aula':'Monitoreo de aulas'}</h1><p className="muted">{selected?.school||'Espacio educativo'} · {demo?'Vista de ejemplo':({admin:'Administración',docente:'Docente',observador:'Observador'}[myRole||'']||'Sin aula seleccionada')}</p></div><div className="portal-context"><label className="room-select"><span>Aula seleccionada</span><StyledSelect label="Aula seleccionada" value={room} onChange={e=>{setBusy(false);setAttentionTarget(null);setRoom(e.target.value);setReadings([])}}>{!rooms.length&&<option value="">Todavía no hay aulas asignadas</option>}{rooms.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</StyledSelect></label><button className="secondary refresh-control" aria-label="Actualizar" disabled={busy||demo} onClick={()=>{void refresh();void administration.reload()}}><RefreshCw size={17}/><span>Actualizar</span></button></div></header>}
 <PortalBoundary resetKey={`${session.epoch}:${page}:${room}`} onRecover={page==='aulas'?undefined:()=>navigate('aulas')}><div className="portal-page" key={page}>
 {demo&&<div className="banner demo-banner"><b>DEMOSTRACIÓN</b><span>Datos ficticios · Sin cambios ni envíos reales</span></div>}
 {!demo&&!online&&!overviewLoading&&<div className="banner error" role="alert">No se pudo verificar el estado remoto. La información conservada puede estar desactualizada y las acciones están bloqueadas.{refreshError&&<small className="connection-detail">{refreshError}</small>}</div>}
 {notice&&<div className="notice" role="status">{notice}<button aria-label="Cerrar aviso" onClick={()=>setNotice('')}>×</button></div>}
 {incidents.some(i=>i.status!=='resuelto')&&page!=='incidentes'&&(page!=='gestion'||incidents.some(i=>i.source==='arduino'&&i.status!=='resuelto'))&&<section className={'attention-strip '+(incidents.some(i=>i.source==='arduino'&&i.status!=='resuelto')?'urgent':'simulation')} role="status"><Bell size={24}/><div><b>{incidents.filter(i=>i.status!=='resuelto').length} {incidents.filter(i=>i.status!=='resuelto').length===1?'aviso por revisar':'avisos por revisar'}</b><p>{incidents.some(i=>i.source==='arduino'&&i.status!=='resuelto')?'Revise el aula y registre la atención. La decisión corresponde al responsable.':'SIMULACIÓN · Hay una prueba pendiente de revisión. No representa una medición física.'}</p></div><button onClick={()=>navigate('incidentes')}>Revisar avisos</button></section>}

 {page==='aulas'&&<ClassroomScreen rooms={rooms} selected={selected} snapshots={snapshots} localObservation={liveObservation} incidents={incidents} clock={clock} demo={demo} canConnect={myRole==='admin'} onPageChange={navigate}/>}
 {page==='incidentes'&&<IncidentsScreen incidents={incidents} deliveries={view?.deliveries||[]} online={online} busy={busy} demo={demo} incidentFilter={incidentFilter} onFilter={setIncidentFilter} onAttention={attention} onDirectAttention={item=>void attendDirect(item)}/>}
 {attentionTarget&&<AttentionDialog key={attentionTarget.id+attentionTarget.action} target={attentionTarget} room={selected?.name||'Aula'} allowed={canSaveAttention} demo={demo} onClose={()=>setAttentionTarget(null)} onSave={saveAttention}/>}
 {page==='historial'&&<HistoryScreen source={source} onSourceChange={value=>{setBusy(false);setSource(value);setReadings([])}} readings={readings} onQuery={()=>void history()} online={online} demo={demo} busy={busy} room={room}/>}
 {page==='arduino'&&myRole==='admin'&&(hostedPortal?<section className="card hosted-arduino-help"><h2>Conecta el Arduino desde su PC</h2><p>Abre Panel SFA Aire en la computadora conectada por USB, ingresa con tu cuenta y selecciona {selected?.name||'el aula'}. En Conexión Arduino podrás buscar puertos y comenzar a medir.</p><p>Este portal recibe las mediciones en la nube. Puedes consultarlas y atender los avisos desde cualquier equipo.</p><div className="hosted-local-link"><a href="http://127.0.0.1:8767/remoto?view=arduino" target="_blank" rel="noopener noreferrer">Abrir el panel instalado en esta PC</a><small>El panel local debe estar iniciado en esta computadora.</small></div></section>:null)}
 {page==='gestion'&&canAdminister&&<AdministrationScreen key={`${session.epoch}:${room}`} room={room} rooms={rooms} onArduino={()=>navigate('arduino')} onSelect={id=>{setRoom(id);setReadings([])}} invoke={(name,body)=>service.invoke(name,body)} demo={demo} online={online} capabilities={administration.state} reloadCapabilities={administration.reload} connection={{url,key:publicKey}} contextKey={`${session.epoch}:${room}`} rpc={rpc} onChanged={refresh} onCreated={id=>{setRoom(id);setNotice('Aula creada y seleccionada.')}}/>}
 {page==="laboratorio"&&myRole==="admin"&&<Suspense fallback={<section className="card" role="status">Cargando laboratorio…</section>}><AdminLab key={room} room={room} demo={demo} rpc={rpc}/></Suspense>}
 </div></PortalBoundary>
 {myRole==='admin'&&!hostedPortal&&<div hidden={page!=='arduino'}><PortalBoundary resetKey={`${session.epoch}:${room}`}><Suspense fallback={<section className="card" role="status">Cargando conexión Arduino…</section>}><ArduinoScreen key={session.epoch+':'+room} room={room} name={selected?.name||'su aula'} classrooms={rooms} demo={demo} active={page==='arduino'} local={local}/></Suspense></PortalBoundary></div>}
 <footer><span>SFA Aire · Portal remoto · Desarrollo</span><span>MQ135 relativo · Datos y simulaciones identificados</span></footer></main></div>
}
