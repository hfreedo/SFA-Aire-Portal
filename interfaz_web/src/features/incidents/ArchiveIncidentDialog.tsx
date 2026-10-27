import ReasonDialog from '../../shared/dialogs/ReasonDialog';
import type {AttentionTarget} from '../../AttentionDialog';
type Props={target:AttentionTarget;room:string;allowed:boolean;demo:boolean;onClose:()=>void;onSave:(note:string)=>Promise<void>};
export default function ArchiveIncidentDialog({target,room,allowed,demo,onClose,onSave}:Props){
 return <ReasonDialog title="Archivar administrativamente" description="Cierre de seguimiento para un receptor retirado o un ensayo terminado o vencido. La coordinación vigente debe justificar esta decisión." warning="Este archivo NO confirma normalización del ambiente, comprensión ni ejecución de indicaciones. Si hay riesgo real, mantenga el protocolo institucional por el canal acordado." context={`${room} · ${target.source==='simulacion'?'SIMULACIÓN':'ARDUINO'} · Abierto el ${target.opened}`} label="Motivo del archivo administrativo" confirmLabel="Confirmar archivo administrativo" allowed={allowed} demo={demo} onClose={onClose} onSave={onSave}/>;
}
