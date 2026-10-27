package org.sfa.aire

import android.app.Activity
import android.app.Instrumentation
import android.app.PendingIntent
import android.content.ComponentName
import android.content.Intent
import android.net.Uri
import org.sfa.aire.data.session.LanConnectionRepository

/** Solo emulador propio sin conexiones. La prueba shell externa vive en android_entry_audit.py. */
class EntryBoundaryChecks(private val instrumentation:Instrumentation){
    fun verify(){
        val context=instrumentation.targetContext
        val manager=context.packageManager
        check(manager.getActivityInfo(ComponentName(context,LauncherActivity::class.java),0).exported)
        check(!manager.getActivityInfo(ComponentName(context,MainActivity::class.java),0).exported)
        check(!manager.getActivityInfo(ComponentName(context,CloudActivity::class.java),0).exported)
        check(!manager.getServiceInfo(ComponentName(context,AireMessagingService::class.java),0).exported)
        val launch=manager.getLaunchIntentForPackage(context.packageName)?:error("No launcher")
        check(launch.component?.className==LauncherActivity::class.java.name)
        check(!CloudApi.hasSession(context)&&LanConnectionRepository(context).read()==null){"Entry fixture requires clean emulator connections"}
        val prefs=Api.prefs(context)
        val oldRoute=prefs.getString("push_route",null)
        val oldRoom=prefs.getString("cloud_room",null)
        val oldReceipts=prefs.getStringSet("receipts",null)?.toSet()
        val generation=LanConnectionRepository(context).generation()
        val delivery="12121212-1212-4212-8212-121212121212"
        val injectedRoom="34343434-3434-4434-8434-343434343434"
        var cloud:Activity?=null;var local:Activity?=null
        try {
            prefs.edit().putString("push_route","local").remove("cloud_room").putStringSet("receipts",emptySet()).commit()
            // La actividad pública no copia extras, URI, acción o flags externos al destino.
            val monitor=instrumentation.addMonitor(CloudActivity::class.java.name,null,false)
            context.startActivity(Intent(context,LauncherActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                .setAction("untrusted.action").setData(Uri.parse("sfa-aire://untrusted"))
                .putExtra("delivery_id",delivery).putExtra("classroom_id",injectedRoom)
                .putExtra("local",true).putExtra("demo",true)
                .putExtra("notification_generation",0L).putExtra("notification_binding","untrusted"))
            cloud=instrumentation.waitForMonitorWithTimeout(monitor,10000)?:error("Public launcher did not open workspace")
            instrumentation.removeMonitor(monitor);instrumentation.waitForIdleSync()
            check(cloud.intent.data==null&&cloud.intent.action==null&&cloud.intent.extras==null)
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
            check(!prefs.contains("cloud_room"))
            // El PendingIntent propio conserva la apertura interna, pero sin handshake no atribuye acuse.
            val localMonitor=instrumentation.addMonitor(MainActivity::class.java.name,null,false)
            val pending=PendingIntent.getActivity(context,9917,Intent(context,MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).setData(Uri.parse("sfa-aire://entry-fixture/$delivery"))
                .putExtra("delivery_id",delivery).putExtra("lan_generation",generation),PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE)
            pending.send()
            local=instrumentation.waitForMonitorWithTimeout(localMonitor,10000)?:error("Internal LAN PendingIntent did not open")
            instrumentation.removeMonitor(localMonitor);instrumentation.waitForIdleSync()
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
            // Un PendingIntent capturado antes de cambiar conexión tampoco puede abrir un acuse nuevo.
            prefs.edit().putStringSet("receipts",emptySet()).commit()
            instrumentation.runOnMainSync{local?.finish()};local=null
            val staleMonitor=instrumentation.addMonitor(MainActivity::class.java.name,null,false)
            context.startActivity(Intent(context,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                .putExtra("delivery_id",delivery).putExtra("lan_generation",generation-1))
            local=instrumentation.waitForMonitorWithTimeout(staleMonitor,10000)?:error("Stale LAN fixture did not open")
            instrumentation.removeMonitor(staleMonitor);instrumentation.waitForIdleSync()
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
            // La misma apertura interna deja de acusar al cambiar la ruta activa a cloud.
            prefs.edit().putString("push_route","cloud").putStringSet("receipts",emptySet()).commit()
            instrumentation.runOnMainSync{local?.finish()};local=null
            val inactiveMonitor=instrumentation.addMonitor(MainActivity::class.java.name,null,false)
            context.startActivity(Intent(context,MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK).putExtra("delivery_id",delivery).putExtra("lan_generation",generation))
            local=instrumentation.waitForMonitorWithTimeout(inactiveMonitor,10000)?:error("LAN route fixture did not open")
            instrumentation.removeMonitor(inactiveMonitor);instrumentation.waitForIdleSync()
            check(prefs.getStringSet("receipts",emptySet())!!.isEmpty())
        }finally{
            instrumentation.runOnMainSync{local?.finish();cloud?.finish()}
            val edit=prefs.edit()
            if(oldRoute==null)edit.remove("push_route") else edit.putString("push_route",oldRoute)
            if(oldRoom==null)edit.remove("cloud_room") else edit.putString("cloud_room",oldRoom)
            if(oldReceipts==null)edit.remove("receipts") else edit.putStringSet("receipts",oldReceipts)
            check(edit.commit())
        }
    }
}
