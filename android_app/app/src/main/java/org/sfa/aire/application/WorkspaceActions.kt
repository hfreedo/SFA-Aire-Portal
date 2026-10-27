package org.sfa.aire.application

import android.content.Context
import org.json.JSONObject
import org.sfa.aire.Api
import org.sfa.aire.CloudApi
import org.sfa.aire.data.network.EndpointPolicy
import org.sfa.aire.data.session.SessionRepository

data class WorkspaceResult(val data:JSONObject,val generation:Long)

data class PublicConnection(val url:String,val key:String){val configured:Boolean get()=url.isNotBlank()&&key.isNotBlank()}
/** Casos de uso del espacio remoto. No construye ni modifica vistas. */
class WorkspaceActions(private val context:Context){
    fun connection():PublicConnection {
        val prefs=Api.prefs(context)
        val defaults=try{context.assets.open("sfa-public.json").bufferedReader().use{JSONObject(it.readText())}}catch(_:Exception){JSONObject()}
        return PublicConnection(prefs.getString("cloud_url",null)?.takeIf{it.isNotBlank()}?:defaults.optString("url"),prefs.getString("cloud_key",null)?.takeIf{it.isNotBlank()}?:defaults.optString("publishable_key"))
    }
    fun login(email:String,password:String):WorkspaceResult {
        val config=connection();val target=EndpointPolicy.cloud(config.url,config.key)
        require(email.trim().isNotEmpty()&&password.isNotEmpty()){"Escriba correo y contraseña"}
        CloudApi.logout(context)
        Api.prefs(context).edit().putString("cloud_url",target).putString("cloud_key",config.key).putString("cloud_email",email.trim()).apply()
        CloudApi.login(context,email,password)
        return refresh()
    }
    fun refresh():WorkspaceResult {
        val generation=SessionRepository(context).generation()
        val data=CloudApi.overview(context)
        check(generation==SessionRepository(context).generation()){"La sesión cambió. Actualice el acceso"}
        return WorkspaceResult(data,generation)
    }
    fun execute(command:CareCommand,generation:Long){
        CloudApi.rpc(context,command.name,command.arguments,generation)
    }
    fun registerPhone(token:String,acceptSimulations:Boolean,generation:Long):WorkspaceResult {
        check(SessionRepository(context).generation()==generation){"La sesión cambió. Vuelva a registrar el teléfono"}
        Api.prefs(context).edit().putBoolean("cloud_simulations",acceptSimulations).apply()
        CloudApi.register(context,token,generation)
        check(SessionRepository(context).generation()==generation){"La sesión cambió. Verifique el registro del teléfono"}
        Api.prefs(context).edit().putString("fcm_token",token).putString("push_route","cloud").apply()
        return refresh()
    }
    fun notificationRegistered(room:String):Boolean {
        val session=SessionRepository(context).notificationSession()?:return false
        val p=Api.prefs(context)
        return p.getString("push_route","none")=="cloud"&&p.getString("cloud_push_binding",null)==session.binding&&p.getString("cloud_push_room",null)==room
    }
    fun logout():Boolean {
        var unlinked=true
        try{CloudApi.rpc(context,"aire_unregister_phone",JSONObject().put("p_installation_id",CloudApi.notificationBinding(context)))}catch(_:Exception){unlinked=false}
        finally{CloudApi.logout(context)}
        return unlinked
    }
}
