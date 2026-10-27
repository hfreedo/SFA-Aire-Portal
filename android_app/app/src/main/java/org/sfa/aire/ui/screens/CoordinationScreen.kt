package org.sfa.aire.ui.screens
import android.widget.LinearLayout
import android.view.View
import android.graphics.Color
import org.json.JSONObject
import org.sfa.aire.ui.AireUi
import org.sfa.aire.domain.CarePolicy

interface CoordinationEvents {
    fun take(item:JSONObject)
    fun attend(item:JSONObject)
    fun respond(instruction:JSONObject,action:String,title:String)
    fun issue(item:JSONObject)
    fun close(item:JSONObject)
}
class CoordinationScreen(private val ui:AireUi,private val events:CoordinationEvents,private val allowed:Boolean){
    fun render(box:LinearLayout,item:JSONObject,panel:JSONObject){with(ui){

        val actor=panel.getString("user_id");val duty=panel.optJSONObject("duty")
        val people=panel.getJSONArray("people")
        fun label(id:String):String=(0 until people.length()).map{people.getJSONObject(it)}.firstOrNull{it.getString("id")==id}?.getString("label")?:"Sin asignar"
        val current=item.optString("coordinator_id", "")
        val permissions=CarePolicy.permissions(actor,current,duty?.optString("coordinator"),duty?.optString("teacher"),duty?.optString("deputy"),item.getString("status"))
        meta(box,"Coordinación",label(current))
        meta(box,"Responsable",label(duty?.optString("teacher")?:""))
        if(permissions.canTake)actionButton(box,"Asumir coordinación",allowed){events.take(item)}
        if(permissions.canContext)actionButton(box,"Confirmar atención / contexto",allowed){events.attend(item)}
        val instructions=panel.getJSONArray("instructions")
        val ins=(0 until instructions.length()).map{instructions.getJSONObject(it)}.firstOrNull{it.getString("incident_id")==item.getString("id") && it.getString("status")!="reemplazada"}
        if(ins!=null) {
            val expires=CarePolicy.expiresAt(ins.optString("expires_at"))
            val expiryLabel=if(expires==null)"Sin vigencia verificable" else java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT).format(java.util.Date(expires))
            val expired=expires==null||expires<=System.currentTimeMillis()
            val instruction=card(box,Color.rgb(247,249,245))
            text(instruction,"INDICACIÓN · VERSIÓN ${ins.getInt("version")}",11f,true)
            text(instruction,ins.getString("action"),18f,true)
            text(instruction,ins.getString("reason"),14f)
            meta(instruction,"Responsable",label(ins.getString("recipient")))
            val statuses=mapOf("emitida" to "Pendiente de comprensión","confirmada" to "Comprensión confirmada","aclaracion" to "Solicita aclaración","impedimento" to "Necesita apoyo","realizada" to "Resultado registrado","parcial" to "Resultado parcial","reemplazada" to "Reemplazada")
            meta(instruction,"Respuesta",statuses[ins.getString("status")]?:ins.getString("status"))
            meta(instruction,"Vigencia",expiryLabel+if(expired)" · VENCIDA" else "")
            if(ins.optString("response").isNotBlank())text(instruction,ins.optString("response"),14f)
            if(!permissions.closed){
                val labels=mapOf("confirmada" to "Confirmo la indicación","aclaracion" to "Necesito aclaración","impedimento" to "No puedo ejecutarla","parcial" to "Registrar resultado parcial","realizada" to "Registrar resultado completo")
                for(action in CarePolicy.responses(actor,ins.getString("recipient"),ins.getString("status"),expires,System.currentTimeMillis())){
                    val title=labels.getValue(action)
                    actionButton(box,title,allowed){events.respond(ins,action,title)}
                }
            }
        } else text(box,"Sin indicación emitida. Registre contexto y utilice el protocolo institucional.")
        if(!permissions.closed&&permissions.directing){
            actionButton(box,if(ins==null)"Emitir indicación" else "Reemplazar indicación",allowed){events.issue(item)}
            if(ins==null||ins.getString("status")=="realizada")actionButton(box,"Revisar y cerrar con motivo",allowed){events.close(item)}
        }
        val timeline=panel.getJSONArray("events")
        val recent=(0 until timeline.length()).map{timeline.getJSONObject(it)}.filter{it.getString("incident_id")==item.getString("id")}.take(3)
        if(recent.isNotEmpty()){
            val history=column().apply{visibility=View.GONE}
            secondary(box,"Ver registro de coordinación"){history.visibility=if(history.visibility==View.VISIBLE)View.GONE else View.VISIBLE}.apply{isEnabled=true;alpha=1f}
            box.addView(history)
            for(event in recent)text(history,"${event.getString("kind")} · ${event.optString("notification_state").replace('_',' ')}\n${event.optString("note")}",12f)
        }
        text(box,"Recibir push no confirma comprensión ni ejecución. Si falla la conexión, utilice el canal institucional acordado.",12f)
        }}
}
