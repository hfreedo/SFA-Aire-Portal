package org.sfa.aire

import android.app.Instrumentation
import android.content.Context
import android.content.ContextWrapper
import org.json.JSONObject
import org.sfa.aire.data.notifications.ReceiptCodec
import org.sfa.aire.data.session.LanConnectionRepository
import java.net.InetAddress
import java.net.ServerSocket
import java.util.UUID
import java.util.concurrent.CopyOnWriteArrayList

/** HTTP real únicamente a loopback del emulador; emisor/datos ficticios, nunca FCM/Auth. */
class LocalProtocolChecks(private val instrumentation:Instrumentation){
    private data class Call(val path:String,val body:JSONObject)
    private class Receiver:AutoCloseable {
        val socket=ServerSocket(0,8,InetAddress.getByName("127.0.0.1"))
        val url="http://127.0.0.1:${socket.localPort}"
        @Volatile var receiverId:String?=UUID.randomUUID().toString()
        @Volatile var conflictDelivery:String?=null
        val calls=CopyOnWriteArrayList<Call>()
        private val thread=Thread{
            while(!socket.isClosed){try{socket.accept().use{client->
                client.soTimeout=4000
                val input=client.getInputStream().bufferedReader(Charsets.UTF_8)
                val first=input.readLine()?:return@use
                val path=first.split(' ')[1]
                var length=0;var authorized=false
                while(true){val line=input.readLine()?:break;if(line.isEmpty())break
                    if(line.startsWith("Content-Length:",true))length=line.substringAfter(':').trim().toInt()
                    if(line.equals("Authorization: Bearer fixture-local-only",true))authorized=true
                }
                val body=CharArray(length);var offset=0
                while(offset<length){val count=input.read(body,offset,length-offset);check(count>0);offset+=count}
                val parsed=if(length>0)JSONObject(String(body))else JSONObject()
                calls.add(Call(path,parsed))
                val code=when{!authorized->401;conflictDelivery!=null&&path.contains("/$conflictDelivery/")->409;else->200}
                val response=if(code!=200)JSONObject().put("detail","Contexto retirado")
                    else if(path=="/api/state")JSONObject().put("receiver_id",receiverId?:JSONObject.NULL)
                    else JSONObject().put("ok",true)
                val bytes=response.toString().toByteArray(Charsets.UTF_8)
                client.getOutputStream().apply{
                    write("HTTP/1.1 $code Fixture\r\nContent-Type: application/json\r\nContent-Length: ${bytes.size}\r\nConnection: close\r\n\r\n".toByteArray())
                    write(bytes);flush()
                }
            }}catch(_:Exception){if(socket.isClosed)break}}
        }.apply{isDaemon=true;start()}
        override fun close(){socket.close();thread.join(2000)}
    }
    fun verify(){
        val name="audit-local-v2-loopback"
        val context=object:ContextWrapper(instrumentation.targetContext){
            override fun getApplicationContext():Context=this
            override fun getSharedPreferences(prefName:String,mode:Int)=super.getSharedPreferences(if(prefName=="sfa-aire")name else prefName,mode)
        }
        val prefs=Api.prefs(context)
        try{Receiver().use{server->
            prefs.edit().clear().putString("push_route","local").commit()
            val repo=LanConnectionRepository(context)
            repo.save(server.url,"fixture-local-only")
            val pending=repo.snapshot()!!;check(pending.receiverId==null)
            Api.enqueueReceipt(context,UUID.randomUUID().toString(),"recibido","local",pending.generation,pending)
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
            Api.request(context,"/state",lanSession=pending)
            val verified=repo.snapshot()!!
            check(verified.receiverId==server.receiverId&&verified.generation==pending.generation&&verified.binding==pending.binding)
            check(!verified.registered)
            Api.register(context,"fake-local-fcm-token-not-sent",verified)
            val registration=server.calls.last{it.path=="/api/devices"}.body
            check(registration.getString("receiver_id")==verified.receiverId)
            check(registration.getString("notification_binding")==verified.binding)
            check(repo.snapshot()!!.registered)
            val one=UUID.randomUUID().toString();val two=UUID.randomUUID().toString()
            Api.enqueueReceipt(context,one,"recibido","local",verified.generation,verified)
            Api.enqueueReceipt(context,two,"abierto","local",verified.generation,verified)
            val first=ReceiptCodec.decode(prefs.getStringSet("receipts",emptySet())!!.first())!!
            server.conflictDelivery=first.delivery
            Api.flushReceipts(context)
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
            val receipts=server.calls.filter{it.path.endsWith("/receipt")}
            check(receipts.size==2&&receipts.first().path.contains(first.delivery))
            check(receipts.all{it.body.getString("receiver_id")==verified.receiverId&&it.body.getString("notification_binding")==verified.binding})
            check(prefs.getLong("lan_rejected_receipt_generation",-1)==verified.generation)
            // Cambia la identidad del servidor detrás de la misma URL/clave.
            server.receiverId=UUID.randomUUID().toString()
            Api.enqueueReceipt(context,UUID.randomUUID().toString(),"recibido","local",verified.generation,verified)
            Api.request(context,"/state",lanSession=verified)
            val replaced=repo.snapshot()!!
            check(replaced.receiverId==server.receiverId&&replaced.generation>verified.generation&&replaced.binding!=verified.binding&&!replaced.registered)
            var rejected=false
            try{repo.confirmReceiver(verified,verified.receiverId)}catch(_:IllegalStateException){rejected=true}
            check(rejected&&repo.snapshot()!!.receiverId==server.receiverId)
            val count=server.calls.size
            Api.flushReceipts(context)
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty()&&server.calls.size==count)
            rejected=false
            try{Api.register(context,"old-token-not-sent",verified)}catch(_:IllegalStateException){rejected=true}
            check(rejected&&server.calls.size==count)
            // Receptor anterior sin v2: monitoreo HTTP posible; registro/acuse no se inventan.
            server.receiverId=null
            Api.request(context,"/state",lanSession=replaced)
            val unverified=repo.snapshot()!!;check(unverified.receiverId==null)
            val posts=server.calls.count{it.path=="/api/devices"};rejected=false
            try{Api.register(context,"legacy-receiver-token",unverified)}catch(error:IllegalStateException){rejected=error.message?.contains("identidad local v2")==true}
            check(rejected&&server.calls.count{it.path=="/api/devices"}==posts)
        }}finally{prefs.edit().clear().commit()}
    }
}
