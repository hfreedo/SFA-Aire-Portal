package org.sfa.aire.application
import org.json.JSONObject

class CareCommand internal constructor(val name:String,val arguments:JSONObject)
/** Contratos de atención centralizados. El RPC mantiene la autorización efectiva. */
object CareCommands {
    private fun note(value:String):String {val text=value.trim();require(text.length in 3..500){"Escriba entre 3 y 500 caracteres"};return text}
    private fun incident(item:JSONObject)=JSONObject().put("p_incident_id",item.getString("id")).put("p_revision",item.getInt("revision"))
    fun take(item:JSONObject,value:String)=CareCommand("aire_take_coordination",incident(item).put("p_note",note(value)))
    fun attention(item:JSONObject,action:String,value:String):CareCommand {
        require(action in listOf("atender","resolver")){"Acción de atención inválida"}
        return CareCommand("aire_attention",incident(item).put("p_action",action).put("p_note",value.trim().also{require(it.length<=500){"Máximo 500 caracteres"}}))
    }
    fun respond(instruction:JSONObject,action:String,value:String):CareCommand {
        require(action in listOf("confirmada","aclaracion","impedimento","realizada","parcial")){"Respuesta inválida"}
        return CareCommand("aire_respond_instruction",JSONObject().put("p_id",instruction.getString("id")).put("p_revision",instruction.getInt("revision")).put("p_action",action).put("p_note",note(value)))
    }
    fun issue(item:JSONObject,id:String,action:String,reason:String,minutes:Int):CareCommand {
        require(minutes in 1..120){"La vigencia debe ser de 1 a 120 minutos"}
        return CareCommand("aire_issue_instruction",incident(item).put("p_id",id).put("p_action",note(action)).put("p_reason",note(reason)).put("p_minutes",minutes))
    }
}
