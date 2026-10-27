package org.sfa.aire.data.network

import java.net.URI
import java.util.Base64
import org.json.JSONObject

/** Único punto de validación de configuración de red. No autoriza usuarios. */
object EndpointPolicy {
    fun cloud(base:String,key:String):String {
        val uri=base(base)
        require(uri.scheme=="https") { "La conexión institucional requiere HTTPS" }
        require(key.length in 8..8192) { "Clave pública inválida" }
        if(key.startsWith("eyJ")) {
            val claims=try { JSONObject(String(Base64.getUrlDecoder().decode(key.split('.')[1]),Charsets.UTF_8)) }
                catch(_:Exception) { throw IllegalArgumentException("Clave pública inválida") }
            require(claims.optString("role")=="anon") { "Use una clave pública anon, nunca una clave privilegiada" }
        } else require(key.startsWith("sb_publishable_")) { "Use una clave pública publishable o anon" }
        return uri.toASCIIString().trimEnd('/')
    }
    fun local(base:String):String {
        val uri=base(base)
        require(uri.scheme in listOf("http","https")) { "Use una dirección HTTP local o HTTPS" }
        require(uri.scheme=="https"||privateHost(uri.host)) { "HTTP se permite solo con una dirección de red privada" }
        return uri.toASCIIString().trimEnd('/')
    }
    private fun base(value:String):URI {
        val uri=try { URI(value.trim()) } catch(_:Exception) { throw IllegalArgumentException("Dirección de conexión inválida") }
        require(!uri.host.isNullOrBlank()&&uri.rawUserInfo==null&&uri.rawQuery==null&&uri.rawFragment==null&&uri.rawPath in listOf("","/")&&uri.port in -1..65535&&uri.port!=0) { "Use solo la dirección base, sin usuario, ruta ni parámetros" }
        return uri
    }
    private fun privateHost(host:String):Boolean {
        if(host.lowercase() in listOf("localhost","::1","[::1]"))return true
        val parts=host.split('.').map{it.toIntOrNull()?:return false}
        if(parts.size!=4||parts.any{it !in 0..255})return false
        return parts[0]==10||parts[0]==127||(parts[0]==192&&parts[1]==168)||(parts[0]==172&&parts[1] in 16..31)
    }
}
