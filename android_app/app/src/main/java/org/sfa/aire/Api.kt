package org.sfa.aire

import org.sfa.aire.data.network.JsonTransport
import org.sfa.aire.data.network.HttpFailure
import org.sfa.aire.data.session.LanConnectionRepository
import org.sfa.aire.data.session.LanSession
import org.sfa.aire.data.session.SessionRepository
import org.sfa.aire.data.notifications.ReceiptCodec
import android.content.Context
import org.json.JSONObject
import java.util.UUID

object Api {
    fun prefs(c: Context) = c.getSharedPreferences("sfa-aire", Context.MODE_PRIVATE)
    fun installation(c:Context):String=SessionRepository(c).installation()
    fun request(c: Context, path: String, method: String = "GET", body: JSONObject? = null,lanSession:LanSession?=null): JSONObject {
        val repository=LanConnectionRepository(c)
        val session=lanSession?:repository.snapshot()?:throw IllegalStateException("Configure la conexión con la PC")
        check(repository.isCurrent(session)){"La conexión con la PC cambió"}
        val connection=session.connection
        val response=JsonTransport.request(connection.server+"/api"+path,method,mapOf("Authorization" to ("Bearer "+connection.key)),body,"detail")
        check(repository.isCurrent(session)){"La conexión con la PC cambió"}
        if(path=="/state"&&method=="GET")repository.confirmReceiver(session,response.optString("receiver_id").takeIf{LanConnectionRepository.validId(it)})
        return response
    }
    fun register(c: Context, token: String,lanSession:LanSession?=null) {
        val p = prefs(c)
        p.edit().putString("fcm_token", token).apply()
        val route=p.getString("push_route","none")
        if(lanSession!=null)check(route=="local"&&LanConnectionRepository(c).isCurrent(lanSession)){"La conexión con la PC cambió"}
        if(route=="cloud"){if(CloudApi.hasSession(c))CloudApi.register(c,token);return}
        if(route!="local")return
        val repository=LanConnectionRepository(c)
        val captured=lanSession?:repository.snapshot()?:throw IllegalStateException("Configure la conexión con la PC")
        request(c,"/state",lanSession=captured)
        val verified=repository.snapshot()?:throw IllegalStateException("Configure la conexión con la PC")
        check(repository.isCurrent(captured)&&verified.binding==captured.binding){"La conexión con la PC cambió"}
        check(verified.receiverId!=null){"Receptor sin identidad local v2. Actualice la PC antes de registrar avisos"}
        request(c, "/devices", "POST", JSONObject().put("installation_id", installation(c))
            .put("token", token).put("name", android.os.Build.MODEL)
            .put("accept_simulations", p.getBoolean("simulations", false)).put("notification_binding",verified.binding)
            .put("receiver_id",verified.receiverId),verified)
        repository.markRegistered(verified)
    }
    @Synchronized fun enqueueReceipt(c: Context, delivery: String, action: String, route:String="local",expectedGeneration:Long?=null,expectedLan:LanSession?=null) {
        if(route=="cloud"&&!CloudApi.hasSession(c))return
        val p = prefs(c)
        val queue = p.getStringSet("receipts", emptySet())!!.toMutableSet()
        val lan=if(route=="local")try{LanConnectionRepository(c).snapshot()}catch(_:Exception){null}else null
        if(route=="local"&&(lan?.receiverId==null||expectedLan!=null&&(lan.generation!=expectedLan.generation||lan.binding!=expectedLan.binding||lan.receiverId!=expectedLan.receiverId)))return
        val generation=if(route=="cloud")SessionRepository(c).generation()else lan?.generation
        if(expectedGeneration!=null&&generation!=expectedGeneration)return
        val encoded=ReceiptCodec.encode(route,delivery,action,generation,lan?.receiverId,lan?.binding)?:return
        if(queue.size>=256&&!queue.contains(encoded)){p.edit().putBoolean("receipts_overflow",true).commit();return}
        queue.add(encoded)
        p.edit().putStringSet("receipts", queue).commit()
    }
    @Synchronized fun clearCloudReceipts(c:Context){
        val p=prefs(c)
        val local=p.getStringSet("receipts",emptySet())!!.filterNot{it.startsWith("cloud|")||it.startsWith("cloud@")||it.startsWith("cloud2@")}.toSet()
        check(p.edit().putStringSet("receipts",local).commit()){"No se pudo limpiar la cola de la sesión"}
    }
    fun flushReceipts(c: Context) {
        val p = prefs(c)
        val pending = synchronized(this) { p.getStringSet("receipts", emptySet())!!.toList() }
        for (item in pending.take(16)) {
            val receipt=ReceiptCodec.decode(item)
            if(receipt==null){removeReceipt(c,item);continue}
            try {
                if(receipt.route=="cloud"){
                    if(receipt.generation!=SessionRepository(c).generation()||!CloudApi.hasSession(c)){removeReceipt(c,item);continue}
                    CloudApi.rpc(c,"aire_receipt",JSONObject().put("p_delivery_id",receipt.delivery).put("p_installation_id",CloudApi.notificationBinding(c,receipt.generation)).put("p_action",receipt.action),receipt.generation)
                }else {
                    val repository=LanConnectionRepository(c)
                    if(receipt.generation==null||receipt.receiverId==null||receipt.binding==null||receipt.generation!=repository.generation()){removeReceipt(c,item);continue}
                    val session=repository.snapshot()?:continue
                    if(session.generation!=receipt.generation||session.receiverId!=receipt.receiverId||session.binding!=receipt.binding){removeReceipt(c,item);continue}
                    request(c,"/deliveries/${receipt.delivery}/receipt","POST",JSONObject().put("installation_id",installation(c)).put("action",receipt.action)
                        .put("notification_binding",receipt.binding).put("receiver_id",receipt.receiverId),session)
                }
                removeReceipt(c,item)
            }catch(error:Exception){
                if(receipt.route=="local"&&error is HttpFailure&&error.status in listOf(404,409,410)){
                    removeReceipt(c,item)
                    p.edit().putLong("lan_rejected_receipt_generation",receipt.generation?:-1).apply()
                    continue
                }
                break
            }
        }
    }
    @Synchronized private fun removeReceipt(c:Context,item:String){
        val p=prefs(c);val remaining=p.getStringSet("receipts",emptySet())!!.toMutableSet()
        remaining.remove(item);p.edit().putStringSet("receipts",remaining).commit()
    }
}
