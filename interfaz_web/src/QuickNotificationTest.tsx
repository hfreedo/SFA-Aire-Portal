import {useCallback,useEffect,useRef,useState} from 'react';
import {Bell,RefreshCw,Smartphone,CheckCircle2} from 'lucide-react';
type Test={id:string;created_at:string;temperature:number;humidity:number;mq_raw:number;queued:number;accepted:number;received:number;opened:number;pending:number;failed:number;deliveries:{status:string;error:string|null;attempts:number}[]};
type Panel={cloud_ready:boolean;cloud_error?:string|null;eligible_phones:number;remaining:number;runs_remaining:number;tests:Test[]};
type Props={room:string;demo:boolean;rpc:(name:string,args?:Record<string,unknown>)=>Promise<any>};
export default function QuickNotificationTest({room,demo,rpc}:Props){
 const [panel,setPanel]=useState<Panel|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[profile,setProfile]=useState('ambos'),[clock,setClock]=useState(Date.now());
 const alive=useRef(true),request=useRef<string|null>(null),sending=useRef(false),version=useRef(0);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;version.current++}},[]);
 const refresh=useCallback(async(keepError=false)=>{if(demo||sending.current)return;const ticket=++version.current;try{const next=await rpc('aire_notification_test_panel',{p_classroom_id:room});if(alive.current&&ticket===version.current){if(typeof next.cloud_ready!=='boolean'||!Number.isInteger(next.eligible_phones)||!Number.isInteger(next.remaining)||!Number.isInteger(next.runs_remaining)||!Array.isArray(next.tests))throw Error('No se pudo comprobar el estado de las notificaciones.');setPanel(next);if(!keepError)setError('')}}catch(e){if(alive.current&&ticket===version.current){setPanel(null);setError(e instanceof Error?e.message:String(e))}}},[room,demo,rpc]);
 const latest=panel?.tests[0],age=latest?(clock-Date.parse(latest.created_at))/1000:Infinity;
 const tracking=!!latest&&latest.opened<latest.queued&&latest.failed<latest.queued&&age<300;
 useEffect(()=>{void refresh();const id=setInterval(()=>{if(document.visibilityState==='visible')void refresh()},tracking?(age<60?5000:15000):60000);return()=>clearInterval(id)},[refresh,tracking,age<60]);
 useEffect(()=>{const id=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(id)},[]);
 const reason=demo?'Vista de ejemplo: no envía notificaciones.':!panel?'Comprobando el estado de envío…':!panel.cloud_ready?'El emisor cloud necesita configuración.':panel.cloud_error?'El emisor informa un problema de conexión o autorización. Revisa el resultado y actualiza el estado antes de repetir.':panel.eligible_phones===0?'Esta aula aún no tiene teléfonos habilitados. En Android selecciona esta aula y activa las notificaciones de simulación en Ajustes.':panel.runs_remaining<1?'Se alcanzó el máximo preventivo de pruebas de hoy.':panel.remaining<panel.eligible_phones?'El presupuesto de hoy no alcanza para todos los teléfonos habilitados.':latest&&latest.pending>0?'La prueba está en cola. El sistema reintenta el envío automáticamente.':latest&&age<30?'Espera '+Math.ceil(30-age)+' s antes de enviar otra prueba.':'';
 async function send(){
  if(reason||sending.current||demo)return;sending.current=true;version.current++;setBusy(true);setError('');request.current??=crypto.randomUUID();
  try{await rpc('aire_send_test_alert',{p_classroom_id:room,p_request_id:request.current,p_profile:profile});if(!alive.current)return;request.current=null}
  catch(e){if(alive.current)setError(e instanceof Error?e.message:String(e))}
  finally{sending.current=false;if(alive.current){setBusy(false);void refresh(true)}}
 }
 return <section className="card quick-notification"><div className="section-title"><div><p className="eyebrow">PRUEBA RÁPIDA · SOLO ADMINISTRADORES</p><h2><Smartphone size={24}/>Probar la notificación del celular</h2></div><button className="secondary" aria-label="Actualizar estado de la prueba" disabled={busy||demo} onClick={()=>void refresh()}><RefreshCw size={17}/></button></div>
 <p>Envía un aviso identificado como <b>SIMULACIÓN</b> a los teléfonos habilitados de esta aula. Funciona desde la nube, sin conectar Arduino ni configurar una PC.</p>
 {!demo&&panel&&<div className="quick-readiness"><span><Smartphone size={18}/><b>{panel.eligible_phones}</b> {panel.eligible_phones===1?'teléfono habilitado':'teléfonos habilitados'}</span><span>{panel.remaining} entregas de prueba disponibles hoy</span></div>}
 <details className="quick-profiles"><summary>Elegir valores de la prueba</summary><div className="lab-presets">{[['temperatura','Temperatura · 38 °C'],['mq135','MQ135 · 600 ADC'],['ambos','Ambos']].map(([id,label])=><button type="button" key={id} aria-pressed={profile===id} disabled={busy} className={profile===id?'':'secondary'} onClick={()=>{setProfile(id);request.current=null}}>{label}</button>)}</div></details>
 <button className="quick-send" disabled={!!reason||busy} onClick={()=>void send()}><Bell size={19}/>{busy?'Preparando aviso…':'Enviar aviso de prueba'}</button>
 {reason&&<p className="quick-reason" role="status">{reason}</p>}{error&&<div className="banner error" role="alert">{error}</div>}
 {latest&&<div className="quick-result" role="status"><h3><CheckCircle2 size={19}/>{latest.failed>0?'Hay entregas sin confirmar':latest.opened>0?'Aviso abierto en Android':latest.received>0?'Aviso recibido en Android':latest.accepted>0?'Aceptado por Firebase · Esperando el celular':'Aviso en cola de envío'}</h3><p>{new Date(latest.created_at).toLocaleString('es-PY')} · Temperatura {latest.temperature} °C · MQ135 {latest.mq_raw} ADC</p><div className="quick-stages">{[['Programadas',latest.queued],['Aceptadas por FCM',latest.accepted],['Recibidas en app',latest.received],['Abiertas',latest.opened]].map(([label,count])=><div key={label}><strong>{count} / {latest.queued}</strong><span>{label}</span></div>)}</div>
 {latest.failed>0&&<p className="banner error">{latest.failed} entrega(s) terminaron sin recepción confirmada. Revisa la conexión, los permisos y el registro Android. {Array.from(new Set(latest.deliveries.map(d=>d.error).filter(Boolean))).join(' · ')}</p>}
 {latest.accepted>latest.received&&age>=300&&<p>Firebase aceptó el envío, pero falta el acuse del celular. Comprueba su red y el permiso de notificaciones.</p>}
 <small>En cola, aceptado por Firebase, recibido y abierto son estados diferentes. No se afirma recepción hasta obtener el acuse de la app.</small></div>}
 <p className="lab-footnote">Esta prueba manual comprueba el aviso cloud y su registro. Para ensayar la adquisición y la persistencia de los sensores, usa la simulación completa de abajo. Se mantienen las guardas Free / Spark.</p>
 </section>
}
