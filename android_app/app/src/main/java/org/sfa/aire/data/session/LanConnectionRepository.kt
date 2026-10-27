package org.sfa.aire.data.session

import android.content.Context
import org.json.JSONObject
import org.sfa.aire.data.network.EndpointPolicy
import java.util.UUID

data class LanConnection(val server:String,val key:String)
data class LanSession(val connection:LanConnection,val generation:Long,val binding:String,val receiverId:String?,val registered:Boolean=false)

/** Dirección/secreto, identidad verificada y vínculo de avisos pertenecen a una generación. */
class LanConnectionRepository(context:Context,preferenceName:String="sfa-aire",alias:String="sfa-aire.lan-connection.v1") {
    private val prefs=context.applicationContext.getSharedPreferences(preferenceName,Context.MODE_PRIVATE)
    private val cipher=KeystoreCipher(alias,"sfa-aire:lan-connection:v1")
    companion object {
        private val lock=Any()
        fun validId(value:String?):Boolean=try{value!=null&&UUID.fromString(value).toString()==value}catch(_:Exception){false}
    }
    fun generation():Long=synchronized(lock){prefs.getLong("lan_connection_generation",0)}
    fun snapshot():LanSession?=synchronized(lock){
        val connection=read()?:return@synchronized null
        val value=JSONObject(cipher.decrypt(prefs.getString("lan_connection_encrypted",null)!!))
        val binding=value.optString("notification_binding")
        if(!validId(binding)){
            // Metadatos anteriores sin vínculo no se reinterpretan como un registro v2.
            val migrated=LanSession(connection,generation()+1,UUID.randomUUID().toString(),null)
            persist(migrated);return@synchronized migrated
        }
        LanSession(connection,generation(),binding,value.optString("receiver_id").takeIf{validId(it)},value.optBoolean("registered",false))
    }
    fun isCurrent(session:LanSession):Boolean=synchronized(lock){session.generation==generation()}
    fun ifCurrent(session:LanSession,action:()->Unit):Boolean=synchronized(lock){
        if(!isCurrent(session))return@synchronized false
        action();true
    }
    /** Solo el resultado HTTP autenticado de /state puede confirmar la identidad. */
    fun confirmReceiver(session:LanSession,receiverId:String?):LanSession=synchronized(lock){
        check(isCurrent(session)){"La conexión con la PC cambió"}
        val current=snapshot()?:throw IllegalStateException("Configure la conexión con la PC")
        check(current.binding==session.binding){"La conexión con la PC cambió"}
        val receiver=receiverId?.takeIf{validId(it)}
        if(current.receiverId==receiver)return@synchronized current
        val replaced=current.receiverId!=null
        val confirmed=current.copy(receiverId=receiver,registered=false,
            generation=if(replaced)generation()+1 else generation(),
            binding=if(replaced)UUID.randomUUID().toString()else current.binding)
        persist(confirmed);confirmed
    }
    fun markRegistered(session:LanSession)=synchronized(lock){
        check(isCurrent(session)){"La conexión con la PC cambió"}
        val current=snapshot()?:throw IllegalStateException("Configure la conexión con la PC")
        check(current.receiverId!=null&&current.receiverId==session.receiverId&&current.binding==session.binding){"La identidad del receptor cambió"}
        persist(current.copy(registered=true))
        prefs.edit().remove("lan_push_rejected_reason").apply()
    }
    fun read():LanConnection?=synchronized(lock){
        val encrypted=prefs.getString("lan_connection_encrypted",null)
        if(encrypted!=null) {
            try { val data=JSONObject(cipher.decrypt(encrypted));return@synchronized validate(data.getString("server"),data.getString("key")) }
            catch(_:Exception){throw IllegalStateException("No se pudo recuperar la conexión protegida. Introduzca de nuevo la PC y su clave")}
        }
        val server=prefs.getString("server",null)?:return@synchronized null
        val key=prefs.getString("key",null)?:return@synchronized null
        if(server.isBlank()||key.isBlank())return@synchronized null
        save(server,key)
    }
    fun save(server:String,key:String):LanConnection=synchronized(lock){
        val connection=validate(server,key)
        val previous=prefs.getString("lan_connection_encrypted",null)?.let{try{
            val value=JSONObject(cipher.decrypt(it))
            val before=validate(value.getString("server"),value.getString("key"))
            val binding=value.optString("notification_binding")
            if(validId(binding))LanSession(before,generation(),binding,value.optString("receiver_id").takeIf{validId(it)},value.optBoolean("registered",false))else null
        }catch(_:Exception){null}}
        val session=if(previous?.connection==connection)previous else LanSession(connection,generation()+1,UUID.randomUUID().toString(),null)
        persist(session!!);connection
    }
    fun clear()=synchronized(lock){
        check(prefs.edit().remove("lan_connection_encrypted").remove("server").remove("key")
            .putLong("lan_connection_generation",generation()+1).remove("lan_push_rejected_reason").commit()){"No se pudo retirar la conexión local"}
    }
    private fun persist(session:LanSession){
        val data=JSONObject().put("server",session.connection.server).put("key",session.connection.key)
            .put("notification_binding",session.binding).put("receiver_id",session.receiverId?:JSONObject.NULL).put("registered",session.registered)
        check(prefs.edit().putString("lan_connection_encrypted",cipher.encrypt(data.toString())).putLong("lan_connection_generation",session.generation)
            .remove("server").remove("key").commit()){"No se pudo guardar la conexión de forma segura"}
    }
    private fun validate(server:String,key:String):LanConnection {
        val normalized=EndpointPolicy.local(server)
        require(key.isNotBlank()&&key.length<=8192&&!key.any{it=='\r'||it=='\n'}){"Introduzca una clave de conexión válida"}
        return LanConnection(normalized,key)
    }
}
