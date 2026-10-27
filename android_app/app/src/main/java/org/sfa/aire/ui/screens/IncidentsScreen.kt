package org.sfa.aire.ui.screens
import android.graphics.Color
import org.json.JSONObject
import org.sfa.aire.ui.AireUi

/** El aviso se atiende sin asignaciones, instrucciones ni comunicación obligatorias. */
class IncidentsScreen(private val ui:AireUi,private val close:(JSONObject)->Unit,private val allowed:Boolean,private val share:(JSONObject)->Unit){
    fun render(data:JSONObject,incidents:List<JSONObject>){with(ui){
        text(root,"Avisos del aula",22f,true)
        text(root,"Revise el aviso y márquelo como atendido. Compartirlo es opcional.",14f)
        if(incidents.isEmpty()){val box=card();text(box,"Sin avisos registrados",20f,true)}
        for(item in incidents.sortedBy{it.optString("status")=="resuelto"}){
            val closed=item.optString("status")=="resuelto"
            val box=card(color=if(closed)Color.rgb(236,238,241)else Color.rgb(255,239,220))
            text(box,if(item.optString("source")=="simulacion")"SIMULACIÓN" else "ARDUINO",11f,true)
            text(box,if(closed)"Aviso atendido" else if(item.optString("severity")=="alerta")"Revisar el aula" else "Variación sostenida",23f,true)
            val opened=try{java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT).format(java.util.Date(java.time.Instant.parse(item.getString("opened_at")).toEpochMilli()))}catch(_:Exception){"Sin fecha verificable"}
            meta(box,"Inicio",opened)
            val note=item.optString("note").removePrefix("AVISO ATENDIDO · No confirma normalización del ambiente.").trim()
            if(note.isNotBlank())text(box,note)
            if(closed)text(box,"La atención del aviso no confirma normalización del ambiente. Consulte la medición en Mi aula.",13f)
            val deliveries=data.getJSONArray("deliveries")
            val own=(0 until deliveries.length()).map{deliveries.getJSONObject(it)}.filter{it.optString("incident_id")==item.optString("id")}
            text(box,if(own.isEmpty())"Sin entregas registradas" else "Recibidas por la app: "+own.count{!it.isNull("received_at")}+" / "+own.size+" entregas visibles",14f)
            val failed=own.count{it.optString("status") in listOf("error","vencido")}
            if(failed>0)text(box,"$failed entrega${if(failed==1)"" else "s"} sin recepción confirmada por error o vencimiento. Revise el registro del teléfono.",14f)
            val omitted=item.optInt("push_omitted_operational")+item.optInt("push_omitted_laboratory")
            if(omitted>0)text(box,"Límite preventivo diario: $omitted entrega${if(omitted==1)" no se programó" else "s no se programaron"}. El aviso sigue disponible en el monitoreo.",14f,true)
            if(!closed){
                val capabilities=item.optJSONObject("capabilities")
                val canClose=capabilities?.opt("can_resolve")==true
                actionButton(box,"Marcar atendido",allowed&&canClose){close(item)}
                if(!canClose)text(box,capabilities?.optString("resolve_reason")?.takeIf{it.isNotBlank()&&it!="null"}?:"Actualice el servidor para verificar permisos de atención.",12f)
            }
            // Elegir canal o cancelar nunca modifica la atención ni acusa recepción.
            secondary(box,"Compartir aviso"){share(item)}.apply{isEnabled=true;alpha=1f}
        }
    }}
}
