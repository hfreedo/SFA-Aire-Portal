package org.sfa.aire

import org.sfa.aire.data.session.*



import android.app.Instrumentation

import android.app.Activity

import android.os.Bundle

import android.content.Context

import android.content.ContextWrapper

import java.security.KeyStore

import org.json.JSONObject



/** Prueba aislada: preferencias/alias exclusivos y datos ficticios; no usa la red. */

class SessionVaultInstrumentation:Instrumentation() {

    private fun verifyNotificationSessions(){
        val name="audit-notification-fixture";val alias="sfa-aire.audit-notification-fixture"
        val isolated=object:ContextWrapper(targetContext){
            override fun getApplicationContext():Context=this
            override fun getSharedPreferences(prefName:String,mode:Int)=super.getSharedPreferences(if(prefName=="sfa-aire")name else prefName,mode)
        }
        val p=Api.prefs(isolated);val repo=SessionRepository(isolated,alias=alias)
        try {
            p.edit().clear().commit()
            repo.save(CloudSession("account-a","refresh-a",9999999999999),repo.generation())
            val old=repo.notificationSession()!!
            check(SessionRepository(isolated,alias=alias).notificationSession()==old)
            val payload=mapOf("notification_contract" to "2","installation_id" to old.binding,
                "delivery_id" to "22222222-2222-4222-8222-222222222222","classroom_id" to "11111111-1111-4111-8111-111111111111")
            check(org.sfa.aire.data.notifications.NotificationPolicy.accepts(payload,old))
            repo.clear()
            repo.save(CloudSession("account-b","refresh-b",9999999999999),repo.generation())
            val current=repo.notificationSession()!!
            check(old.binding!=current.binding)
            check(!org.sfa.aire.data.notifications.NotificationPolicy.accepts(payload,current))
            var applied=false
            check(!repo.ifCurrentNotification(old){applied=true});check(!applied)
            Api.enqueueReceipt(isolated,payload.getValue("delivery_id"),"abierto","cloud",old.generation)
            check(p.getStringSet("receipts",emptySet())!!.isEmpty())
            check(repo.ifCurrentNotification(current){applied=true});check(applied)
            Api.enqueueReceipt(isolated,payload.getValue("delivery_id"),"recibido","cloud",current.generation)
            check(p.getStringSet("receipts",emptySet())!!.single().startsWith("cloud2@${current.generation}|"))
            repo.clear();applied=false
            check(!repo.ifCurrentNotification(current){applied=true});check(!applied)
        }finally{p.edit().clear().commit();KeyStore.getInstance("AndroidKeyStore").apply{load(null);deleteEntry(alias)}}
    }
    private fun verifyLanContext(){
        val name="audit-lan-context-fixture"
        val isolated=object:ContextWrapper(targetContext){
            override fun getApplicationContext():Context=this
            override fun getSharedPreferences(prefName:String,mode:Int)=super.getSharedPreferences(if(prefName=="sfa-aire")name else prefName,mode)
        }
        val p=Api.prefs(isolated);val repo=LanConnectionRepository(isolated)
        val delivery="12121212-1212-4212-8212-121212121212"
        try {
            p.edit().clear().commit()
            repo.save("http://192.168.1.20:8766","fixture-only-a")
            val pending=repo.snapshot()!!
            check(pending.receiverId==null)
            Api.enqueueReceipt(isolated,delivery,"recibido","local",pending.generation)
            check(p.getStringSet("receipts",emptySet())!!.isEmpty())
            val a=repo.confirmReceiver(pending,"11111111-1111-4111-8111-111111111111")
            check(a.generation==pending.generation)
            repo.save(a.connection.server,a.connection.key);check(repo.snapshot()==a)
            Api.enqueueReceipt(isolated,delivery,"recibido","local",a.generation)
            p.edit().putStringSet("receipts",p.getStringSet("receipts",emptySet())!!+"local|$delivery|abierto").commit()
            repo.save("http://192.168.1.21:8766","fixture-only-b")
            val b=repo.snapshot()!!;check(b.generation>a.generation)
            var applied=false;check(!repo.ifCurrent(a){applied=true});check(!applied)
            var rejected=false
            try{Api.request(isolated,"/state",lanSession=a)}catch(e:IllegalStateException){rejected=e.message=="La conexión con la PC cambió"}
            check(rejected) // rechazo antes de iniciar transporte; no hay red.
            p.edit().putString("push_route","cloud").commit();rejected=false
            try{Api.register(isolated,"fixture-token",a)}catch(e:IllegalStateException){rejected=e.message=="La conexión con la PC cambió"}
            check(rejected) // un registro LAN pendiente tampoco se retargetea al modo cloud.
            Api.flushReceipts(isolated);check(p.getStringSet("receipts",emptySet())!!.isEmpty())
            Api.enqueueReceipt(isolated,delivery,"abierto","local",a.generation)
            check(p.getStringSet("receipts",emptySet())!!.isEmpty())
            Api.enqueueReceipt(isolated,delivery,"abierto","local",b.generation)
            check(p.getStringSet("receipts",emptySet())!!.isEmpty())
            val confirmed=repo.confirmReceiver(b,"22222222-2222-4222-8222-222222222222")
            Api.enqueueReceipt(isolated,delivery,"abierto","local",confirmed.generation,confirmed)
            check(p.getStringSet("receipts",emptySet())!!.single()=="local3@${confirmed.generation}|${confirmed.receiverId}|${confirmed.binding}|$delivery|abierto")
            check(repo.ifCurrent(b){applied=true});check(applied)
            repo.save(b.connection.server,"fixture-new-key");check(!repo.isCurrent(b))
            repo.save(a.connection.server,a.connection.key);check(!repo.isCurrent(a))
            repo.clear();check(repo.snapshot()==null)
        }finally{p.edit().clear().commit()}
    }
    private fun verifyLan(){

        val name="audit-lan-fixture";val alias="sfa-aire.audit-lan-fixture"

        val p=targetContext.getSharedPreferences(name,0)

        val repo=LanConnectionRepository(targetContext,name,alias)

        val first=LanConnection("http://192.168.1.20:8766","fixture-lan-private")

        try {

            p.edit().clear().commit()

            check(repo.read()==null)

            p.edit().putString("server",first.server).putString("key",first.key).commit()

            check(repo.read()==first)

            check(!p.contains("server")&&!p.contains("key"))

            check(p.all.values.none{it.toString().contains(first.key)})

            val envelope=p.getString("lan_connection_encrypted",null)!!

            repo.save("http://192.168.1.21:8766/","second-fixture-private")

            check(repo.read()==LanConnection("http://192.168.1.21:8766","second-fixture-private"))

            var rejected=false

            try { repo.save("http://example.com","invalid-target") }catch(_:IllegalArgumentException){rejected=true}

            check(rejected);check(repo.read()?.key=="second-fixture-private")

            rejected=false

            try {repo.save(first.server,"header\r\ninjection")}catch(_:IllegalArgumentException){rejected=true}

            check(rejected)

            p.edit().putString("lan_connection_encrypted",JSONObject(envelope).put("data","AAAAAAAAAAAAAAAAAAAAAA==").toString())

                .putString("server",first.server).putString("key","legacy-must-not-fallback").commit()

            rejected=false

            try {repo.read()}catch(_:IllegalStateException){rejected=true}

            check(rejected)

            // El formulario puede sustituir un sobre ilegible sin reutilizar el secreto anterior.

            repo.save(first.server,first.key)

            check(repo.read()==first);check(!p.contains("key"))

            val protected=p.getString("lan_connection_encrypted",null)!!

            p.edit().putString("cloud_session_encrypted",protected).commit()

            rejected=false

            try {SessionRepository(targetContext,name,alias).read()}catch(_:IllegalStateException){rejected=true}

            check(rejected) // el propósito AAD impide intercambiar los sobres LAN/cloud.

            repo.clear();check(repo.read()==null)

        }finally{p.edit().clear().commit();KeyStore.getInstance("AndroidKeyStore").apply{load(null);deleteEntry(alias)}}

    }

    private var styleOnly=false
    override fun onCreate(arguments:Bundle?){styleOnly=arguments?.getString("suite")=="style";super.onCreate(arguments);start()}

    override fun onStart(){
        if(styleOnly){
            val result=Bundle()
            try{StyleMotionChecks(this).verify();result.putString("stream","PASS: native selector and measured transition frames; no cloud calls");finish(Activity.RESULT_OK,result)}
            catch(error:Throwable){result.putString("shortMsg","Style/motion check failed: "+error.message);finish(Activity.RESULT_CANCELED,result)}
            return
        }

        val name="audit-session-fixture"

        val alias="sfa-aire.audit-session-fixture"

        val prefs=targetContext.getSharedPreferences(name,0)

        val results=Bundle()

        try {

            check(prefs.edit().clear().commit())

            val repo=SessionRepository(targetContext,name,alias)

            val session=CloudSession("fixture-access-private","fixture-refresh-private",123456789L)

            val generation=repo.generation()

            repo.save(session,generation)

            check(repo.read()==session)

            check(prefs.all.values.none{it.toString().contains(session.access)||it.toString().contains(session.refresh)})

            val encrypted=prefs.getString("cloud_session_encrypted",null)!!

            val envelope=JSONObject(encrypted).put("data","AAAAAAAAAAAAAAAAAAAAAA==")

            prefs.edit().putString("cloud_session_encrypted",envelope.toString()).commit()

            var rejected=false

            try{repo.read()}catch(_:IllegalStateException){rejected=true}

            check(rejected)

            repo.clear()

            check(!repo.hasSession())

            rejected=false

            try{repo.save(session,generation)}catch(_:IllegalStateException){rejected=true}

            check(rejected)

            check(!repo.hasSession())

            prefs.edit().putString("cloud_access",session.access).putString("cloud_refresh",session.refresh).putLong("cloud_expires",session.expires).commit()

            check(repo.read()==session)

            check(!prefs.contains("cloud_access")&&!prefs.contains("cloud_refresh")&&!prefs.contains("cloud_expires"))

            check(prefs.contains("cloud_session_encrypted"))

            repo.clear()

            val isolated=object:ContextWrapper(targetContext){

                override fun getApplicationContext():Context=this

                override fun getSharedPreferences(prefName:String,mode:Int)=super.getSharedPreferences(if(prefName=="sfa-aire")"audit-receipt-fixture" else prefName,mode)

            }

            val receiptPrefs=Api.prefs(isolated);receiptPrefs.edit().clear().commit()

            val delivery="11111111-1111-4111-8111-111111111111"

            receiptPrefs.edit().putString("cloud_access","fixture-only").commit()

            Api.enqueueReceipt(isolated,delivery,"recibido","cloud")

            check(receiptPrefs.getStringSet("receipts",emptySet())!!.single().startsWith("cloud2@0|"))

            receiptPrefs.edit().putLong("cloud_session_generation",1).commit()

            Api.flushReceipts(isolated)

            check(receiptPrefs.getStringSet("receipts",emptySet())!!.isEmpty())

            rejected=false

            try{CloudApi.rpc(isolated,"aire_receipt",JSONObject(),0)}catch(_:IllegalStateException){rejected=true}

            check(rejected)

            Api.enqueueReceipt(isolated,delivery,"abierto","local")

            Api.enqueueReceipt(isolated,delivery,"recibido","cloud")

            Api.clearCloudReceipts(isolated)

            check(receiptPrefs.getStringSet("receipts",emptySet())!!.all{it.startsWith("local2@")})

            receiptPrefs.edit().clear().commit()

            verifyNotificationSessions()
            verifyLan()
            verifyLanContext()
            LocalProtocolChecks(this).verify()

            EntryBoundaryChecks(this).verify()
            CareUiChecks(this).verify()
            VisualRefinementChecks(this).verify()
            StyleMotionChecks(this).verify()

            results.putString("stream","PASS: Keystore roundtrip; no plaintext; tamper rejected; logout clears; stale refresh rejected; legacy migration removes plaintext; stale receipt and request rejected; logout preserves LAN receipts; native note validation/preservation/cancel and instruction validation passed. LAN encrypted roundtrip/migration/tamper/isolation/validation passed. Notification binding and stale publication/open/receipt rejected after account change. LAN generation keeps identical config, rejects stale requests/register/open/receipts after PC or key change, and discards unbound legacy receipts. Local v2 loopback handshake/register/receipt, rotated receiver rejection and HTTP409 queue continuation passed. Public launcher sanitized; internal component exports, internal PendingIntent and inactive LAN route checked. Native telemetry updated without rebuilding views; stale label and historical values verified; registration preference requires explicit save; disclosures verified. No cloud RPC.")

            finish(Activity.RESULT_OK,results)

        }catch(error:Throwable){results.putString("shortMsg","Session verification failed: "+error.javaClass.simpleName+" / "+error.message?.take(240));finish(Activity.RESULT_CANCELED,results)}

        finally {targetContext.getSharedPreferences("audit-receipt-fixture",0).edit().clear().commit();prefs.edit().clear().commit();KeyStore.getInstance("AndroidKeyStore").apply{load(null);deleteEntry(alias)}}

    }

}

