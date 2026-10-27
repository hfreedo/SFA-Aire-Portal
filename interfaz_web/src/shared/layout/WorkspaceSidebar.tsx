import {Wind,School,Bell,RefreshCw,Shield,FlaskConical,Activity,Radio,Settings2,LogOut} from 'lucide-react';
import logo from '../../assets/sfa-aire.png';
type MenuItem={id:string;label:string;icon:typeof Wind;admin?:boolean};
const menus:Record<'cloud'|'local',MenuItem[]>={
 cloud:[{id:'aulas',label:'Mis aulas',icon:School},{id:'incidentes',label:'Avisos',icon:Bell},{id:'historial',label:'Historial',icon:RefreshCw},{id:'arduino',label:'Conexión Arduino',icon:Radio,admin:true},{id:'gestion',label:'Administración',icon:Shield,admin:true},{id:'laboratorio',label:'Laboratorio',icon:FlaskConical,admin:true}],
 local:[{id:'monitor',label:'Monitoreo',icon:Activity},{id:'incidentes',label:'Avisos',icon:Bell},{id:'integracion',label:'Conexiones',icon:Radio},{id:'ajustes',label:'Reglas del aula',icon:Settings2}]
};
type Props={mode:'cloud'|'local';page:string;role?:string;canAdminister?:boolean;online:boolean;connectionLabel:string;pending?:number;onNavigate:(page:string)=>void;onLogout:()=>void};
/** Navegación única. Los permisos efectivos siguen comprobándose en API/RPC. */
export default function WorkspaceSidebar({mode,page,role,canAdminister=false,online,connectionLabel,pending=0,onNavigate,onLogout}:Props){return <aside>
 <div className="brand"><img src={logo} alt=""/><span>SFA <b>Aire</b><small>{mode==='cloud'?'AMBIENTE ESCOLAR':'DIAGNÓSTICO LOCAL'}</small></span></div>
 <nav aria-label="Navegación principal">{menus[mode].filter(item=>!item.admin||(item.id==='gestion'?canAdminister:role==='admin')).map(({id,label,icon:Icon})=><button key={id} className={page===id?'selected':''} aria-current={page===id?'page':undefined} onClick={()=>onNavigate(id)}><Icon size={17} aria-hidden="true"/>{label}{id==='incidentes'&&pending>0&&<b className="count">{pending}</b>}</button>)}</nav>
 <div className="aside-bottom"><span className={'dot '+(online?'on':'')}/>{connectionLabel}<button onClick={onLogout}><LogOut size={16} aria-hidden="true"/>Cerrar sesión</button></div>
 </aside>}
