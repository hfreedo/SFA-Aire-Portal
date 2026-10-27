package org.sfa.aire.ui.screens
import android.graphics.Color
import android.widget.LinearLayout
import org.json.JSONObject
import org.sfa.aire.ui.AireUi

/** Atención directa; compartir y consultar entregas son acciones independientes. */
class IncidentsScreen(private val ui:AireUi,private val close:(JSONObject)->Unit,private val allowed:Boolean,private val share:(JSONObject)->Unit,private val comment:((JSONObject)->Unit)?=null){
    private fun date(raw:String):String=try{java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT,ui.locale).format(java.util.Date(java.time.Instant.parse(raw).toEpochMilli()))}catch(_:Exception){"Sin fecha verificable"}
    fun render(data:JSONObject,incidents:List<JSONObject>){with(ui){
                val pending=incidents.count{it.optString("status")!="resuelto"}
        text(root,if(pending==0)"Sin avisos pendientes" else "$pending ${if(pending==1)"aviso pendiente" else "avisos pendientes"}",14f)
        if(incidents.isEmpty()){val box=card();text(box,"Todo al día",20f,true);text(box,"Los nuevos avisos de esta aula aparecerán aquí.",16f)}
        for(item in incidents.sortedBy{it.optString("status")=="resuelto"}){
            val closed=item.optString("status")=="resuelto"
            val box=card()
            val tags=LinearLayout(activity);box.addView(tags)
            val simulated=item.optString("source")=="simulacion"
            val alert=item.optString("severity")=="alerta"
            badge(tags,if(simulated)"SIMULACIÓN" else "ARDUINO",if(simulated)simulationSurface else sage,if(simulated)simulationInk else green)
            badge(tags,if(closed)"ATENDIDO" else if(alert)"ALERTA · PENDIENTE" else "AVISO · PENDIENTE",if(closed)neutralSurface else if(alert)alertSurface else warningSurface,if(closed)muted else if(alert)alertInk else warningInk)
            text(box,if(closed)"Aviso atendido" else if(item.optString("severity")=="alerta")"Revisar ambiente" else "Variación sostenida",20f,true)
            // La lista ya está filtrada y el contexto del aula permanece en la cabecera.
            text(box,"Inicio · "+date(item.optString("opened_at")),14f)
            if(closed&&!item.isNull("resolved_at")&&item.optString("resolved_at").isNotBlank())text(box,"Atendido · "+date(item.optString("resolved_at")),14f)
            val note=item.optString("note").removePrefix("AVISO ATENDIDO · No confirma normalización del ambiente.").trim()
            if(note.isNotBlank())text(box,note,15f)
            if(closed)text(box,"Consulta Mi aula para conocer la medición actual.",14f)
            val deliveries=data.getJSONArray("deliveries")
            val own=(0 until deliveries.length()).map{deliveries.getJSONObject(it)}.filter{it.optString("incident_id")==item.optString("id")}
            val failed=own.count{it.optString("status") in listOf("error","vencido")}
            val omitted=item.optInt("push_omitted_operational")+item.optInt("push_omitted_laboratory")
            if(failed>0)text(box,"Hay entregas sin recepción confirmada. Revisa los detalles.",14f,true)
            if(omitted>0)text(box,"Límite preventivo alcanzado: hay entregas sin programar.",14f,true)
            if(!closed){
                val capabilities=item.optJSONObject("capabilities")
                val canClose=capabilities?.opt("can_resolve")==true
                actionButton(box,"Marcar atendido",allowed&&canClose){close(item)}
                if(comment!=null)rowAction(box,"Atender con nota","note"){comment.invoke(item)}.apply{isEnabled=isEnabled&&allowed&&canClose;alpha=1f}
                if(!canClose)text(box,capabilities?.optString("resolve_reason")?.takeIf{it.isNotBlank()&&it!="null"}?:"Actualiza el estado para verificar permisos de atención.",14f)
            }
            rowAction(box,"Compartir aviso","share"){share(item)}.apply{isEnabled=true;alpha=1f}
            disclosure(box,"Detalles de entrega","delivery-"+item.optString("id")){body->
                text(body,if(own.isEmpty())"Sin entregas registradas" else "Recibidas por la app: "+own.count{!it.isNull("received_at")}+" / "+own.size+" entregas visibles",14f)
                if(failed>0)text(body,"$failed entregas sin recepción confirmada por error o vencimiento.",14f)
                if(omitted>0)text(body,"$omitted entregas sin programar por el límite diario. El aviso sigue disponible en el monitoreo.",14f)
                text(body,"Recibir o atender un aviso no confirma la normalización del ambiente.",14f)
            }
        }
    }}
}
