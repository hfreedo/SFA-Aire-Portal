package org.sfa.aire

import org.sfa.aire.data.network.EndpointPolicy
import org.sfa.aire.data.network.JsonTransport
import org.sfa.aire.data.session.SessionRepository
import org.sfa.aire.data.session.CloudSession

import android.content.Context
import org.json.JSONObject

object CloudApi {
    private fun http(c:Context,path:String,body:JSONObject,access:String?=null):JSONObject {
        val prefs=Api.prefs(c)
        val key=prefs.getString("cloud_key","")!!
        val base=EndpointPolicy.cloud(prefs.getString("cloud_url","")!!,key)
        val headers=mutableMapOf("apikey" to key)
        if(access!=null)headers["Authorization"]="Bearer $access"
        return JsonTransport.request(base+path,"POST",headers,body)
    }
    private fun sessions(c:Context)=SessionRepository(c)
    fun hasSession(c:Context)=sessions(c).hasSession()
    private fun saveSession(c:Context,data:JSONObject,generation:Long) {
        sessions(c).save(CloudSession(data.getString("access_token"),data.getString("refresh_token"),System.currentTimeMillis()+data.optLong("expires_in",3600)*1000),generation)
    }
    fun login(c:Context,email:String,password:String) {
        val generation=sessions(c).generation()
        saveSession(c,http(c,"/auth/v1/token?grant_type=password",JSONObject().put("email",email.trim()).put("password",password)),generation)
    }
    @Synchronized private fun access(c:Context,expectedGeneration:Long?=null):String {
        val store=sessions(c)
        val generation=store.generation()
        check(expectedGeneration==null||expectedGeneration==generation){"El acuse pertenece a otra sesión"}
        val session=store.read()?:throw IllegalStateException("Inicie sesión en la nube")
        var token=session.access
        if(session.expires<System.currentTimeMillis()+60000) {
            val response=http(c,"/auth/v1/token?grant_type=refresh_token",JSONObject().put("refresh_token",session.refresh))
            saveSession(c,response,generation)
            token=response.getString("access_token")
        }
        check(generation==store.generation()){"La sesión cambió. Vuelva a iniciar sesión"}
        return token
    }
    fun rpc(c:Context,name:String,body:JSONObject=JSONObject(),expectedGeneration:Long?=null):JSONObject = http(c,"/rest/v1/rpc/$name",body,access(c,expectedGeneration))
    fun overview(c:Context):JSONObject {
        val data=rpc(c,"aire_overview")
        val rooms=data.getJSONArray("classrooms")
        if(rooms.length()>0) {
            val p=Api.prefs(c)
            val selected=(0 until rooms.length()).map{rooms.getJSONObject(it)}.firstOrNull{it.getString("id")==p.getString("cloud_room",null)}?:rooms.getJSONObject(0)
            val room=selected.getString("id");p.edit().putString("cloud_room",room).apply()
            // El monitoreo y la atención no dependen de coordinación.
        }
        return data
    }
    fun logout(c:Context) {
        sessions(c).clear()
        Api.clearCloudReceipts(c)
        c.getSystemService(android.app.NotificationManager::class.java).cancelAll()
        Api.prefs(c).edit().remove("cloud_push_binding").remove("cloud_push_room").remove("cloud_room").putString("push_route","none").apply()

    }
    fun notificationBinding(c:Context,expectedGeneration:Long?=null):String {
        val session=sessions(c).notificationSession()?:throw IllegalStateException("Inicie sesión")
        check(expectedGeneration==null||expectedGeneration==session.generation){"La sesión cambió"}
        return session.binding
    }
    fun register(c:Context,token:String,expectedGeneration:Long?=null) {
        val generation=expectedGeneration?:sessions(c).generation()
        val binding=notificationBinding(c,generation)
        val p=Api.prefs(c)
        val room=p.getString("cloud_room",null)?:throw IllegalStateException("Seleccione un aula en Acceso remoto")
        rpc(c,"aire_register_phone_v2",JSONObject().put("p_classroom_id",room).put("p_device_id",Api.installation(c)).put("p_binding",binding)
            .put("p_token",token).put("p_name",android.os.Build.MODEL)
            .put("p_accept_simulations",p.getBoolean("cloud_simulations",false)),generation)
        if(sessions(c).generation()==generation)p.edit().putString("cloud_push_binding",binding).putString("cloud_push_room",room).apply()
    }
}
