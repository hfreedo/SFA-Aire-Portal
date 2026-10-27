import {Component,type ReactNode} from 'react';

/** Contiene fallos de render/carga diferida; no altera la sesión ni reintenta mutaciones. */
export default class PortalBoundary extends Component<{children:ReactNode;resetKey?:string;onRecover?:()=>void},{failed:boolean}>{
 state={failed:false};
 static getDerivedStateFromError(){return {failed:true}}
 componentDidUpdate(previous:Readonly<{resetKey?:string}>){
  if(this.state.failed&&previous.resetKey!==this.props.resetKey)this.setState({failed:false});
 }
 render(){
  if(!this.state.failed)return this.props.children;
  return <section className="card section-recovery" role="alert">
   <h2>No se pudo abrir esta sección</h2>
   <p>Puede faltar conexión o haberse actualizado el portal. Si usas la versión local, comprueba que Panel SFA Aire siga abierto en esta PC.</p>
   <div className="actions">
    {this.props.onRecover&&<button onClick={this.props.onRecover}>Volver a Mis aulas</button>}
    <button className={this.props.onRecover?'secondary':''} onClick={()=>location.reload()}>Recargar portal</button>
   </div>
   <p className="muted">Recargar descarta lo que no hayas guardado en esta pantalla.</p>
  </section>;
 }
}
