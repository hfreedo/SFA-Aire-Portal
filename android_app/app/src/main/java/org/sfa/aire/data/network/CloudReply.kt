package org.sfa.aire.data.network

import org.json.JSONObject
import org.json.JSONTokener

/** Los RPC conservan sus firmas: algunos devuelven UUID o null, no un objeto. */
object CloudReply {
    fun parse(text:String):JSONObject {
        if(text.isBlank() || text.trim()=="null")return JSONObject()
        val value=try {JSONTokener(text).nextValue()}catch(_:Exception){throw IllegalStateException("Respuesta remota no válida")}
        return if(value is JSONObject)value else JSONObject().put("result",value)
    }
}
