package org.sfa.aire.data.session

import android.content.Context
import org.json.JSONObject
import java.util.UUID
import org.sfa.aire.data.notifications.NotificationPolicy
import org.sfa.aire.data.notifications.NotificationSession

data class CloudSession(val access:String,val refresh:String,val expires:Long)
/** Una sola frontera de persistencia. Las pantallas nunca leen tokens de preferencias. */
class SessionRepository(context:Context,preferenceName:String="sfa-aire",alias:String="sfa-aire.cloud-session.v1") {
    private val prefs=context.applicationContext.getSharedPreferences(preferenceName,Context.MODE_PRIVATE)
    private val cipher=KeystoreCipher(alias,"sfa-aire:cloud-session:v1")
    companion object { private val lock=Any() }
    fun installation():String=synchronized(lock){
        prefs.getString("installation",null)?:UUID.randomUUID().toString().also{
            check(prefs.edit().putString("installation",it).commit()){"No se pudo guardar la identidad del dispositivo"}
        }
    }
    fun notificationSession():NotificationSession?=synchronized(lock){
        if(!hasSession())return@synchronized null
        NotificationSession(generation(),NotificationPolicy.binding(installation(),generation()))
    }
    fun ifCurrentNotification(session:NotificationSession,action:()->Unit):Boolean=synchronized(lock){
        if(notificationSession()!=session)return@synchronized false
        action();true
    }
    fun hasSession():Boolean=synchronized(lock){prefs.contains("cloud_session_encrypted")||!prefs.getString("cloud_access",null).isNullOrBlank()}
    fun generation():Long=synchronized(lock){prefs.getLong("cloud_session_generation",0)}
    fun read():CloudSession?=synchronized(lock){
        val encrypted=prefs.getString("cloud_session_encrypted",null)
        if(encrypted!=null)return@synchronized decode(encrypted)
        val access=prefs.getString("cloud_access",null)?:return@synchronized null
        val refresh=prefs.getString("cloud_refresh",null)?:throw IllegalStateException("Vuelva a iniciar sesión")
        val session=CloudSession(access,refresh,prefs.getLong("cloud_expires",0))
        // Cifrado y retiro de los campos anteriores en una única edición del mismo archivo.
        save(session,generation())
        session
    }
    fun save(session:CloudSession,expectedGeneration:Long)=synchronized(lock){
        check(expectedGeneration==generation()){"La sesión cambió. Vuelva a iniciar sesión"}
        require(session.access.isNotBlank()&&session.refresh.isNotBlank()){"Sesión incompleta"}
        val value=JSONObject().put("access",session.access).put("refresh",session.refresh).put("expires",session.expires).toString()
        val envelope=cipher.encrypt(value)
        check(prefs.edit().putString("cloud_session_encrypted",envelope.toString()).remove("cloud_access").remove("cloud_refresh").remove("cloud_expires").commit()){"No se pudo guardar la sesión de forma segura"}
    }
    fun clear():Long=synchronized(lock){
        val next=generation()+1
        check(prefs.edit().remove("cloud_session_encrypted").remove("cloud_access").remove("cloud_refresh").remove("cloud_expires").putLong("cloud_session_generation",next).commit()){"No se pudo cerrar la sesión local"}
        next
    }
    private fun decode(encoded:String):CloudSession {
        try {
            val session=JSONObject(cipher.decrypt(encoded))
            return CloudSession(session.getString("access"),session.getString("refresh"),session.getLong("expires"))
        }catch(_:Exception){throw IllegalStateException("No se pudo recuperar la sesión protegida. Vuelva al acceso e inicie sesión")}
    }
}
