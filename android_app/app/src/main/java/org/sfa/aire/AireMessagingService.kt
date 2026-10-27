package org.sfa.aire

import org.sfa.aire.data.notifications.NotificationPolicy
import org.sfa.aire.data.notifications.LocalNotificationPolicy
import org.sfa.aire.data.session.SessionRepository
import org.sfa.aire.data.session.LanConnectionRepository
import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class AireMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        Api.prefs(this).edit().putString("fcm_token", token).apply()
        Thread { try { Api.register(this, token) } catch (_: Exception) {} }.start()
    }
    override fun onMessageReceived(message: RemoteMessage) {
        val delivery = message.data["delivery_id"] ?: return
        if(message.data["channel"] !in listOf(null,"local","cloud"))return
        val route=if(message.data["channel"]=="cloud")"cloud" else "local"
        val repository=SessionRepository(this)
        val session=if(route=="cloud")repository.notificationSession()?:return else null
        if(session!=null&&!NotificationPolicy.accepts(message.data,session))return
        if(Api.prefs(this).getString("push_route","none")!=route)return
        val lanRepository=LanConnectionRepository(this)
        val lanSession=if(route=="local")try{lanRepository.snapshot()?:return}catch(_:Exception){return}else null
        if(lanSession!=null&&!LocalNotificationPolicy.accepts(message.data,lanSession)){
            Api.prefs(this).edit().putString("lan_push_rejected_reason","Se descartó un aviso local sin identidad o vínculo vigente. Actualice el receptor y registre este teléfono.").apply()
            return
        }
        if(lanSession!=null)Api.prefs(this).edit().remove("lan_push_rejected_reason").apply()
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("aula_alerts", "Alertas del aula", NotificationManager.IMPORTANCE_HIGH))
        Api.enqueueReceipt(this, delivery, "recibido",route,session?.generation?:lanSession?.generation,lanSession)
        val intent = Intent(this, if(route=="cloud") CloudActivity::class.java else MainActivity::class.java).putExtra("delivery_id", delivery)
            .putExtra("classroom_id",message.data["classroom_id"])
            .putExtra("lab_run_id",message.data["lab_run_id"])
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        if(session!=null)intent.putExtra("notification_generation",session.generation).putExtra("notification_binding",session.binding)
        if(lanSession!=null)intent.putExtra("lan_generation",lanSession.generation).putExtra("local_receiver_id",lanSession.receiverId).putExtra("local_notification_binding",lanSession.binding)
        intent.data=android.net.Uri.parse("sfa-aire://notification/$route/${session?.binding?:lanSession?.generation.toString()}/$delivery")
        val pending = PendingIntent.getActivity(this, delivery.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        if (Build.VERSION.SDK_INT < 33 || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            val notification=Notification.Builder(this, "aula_alerts")
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle(message.data["title"] ?: "SFA Aire")
                .setContentText(message.data["body"] ?: "Revise el aula")
                .setStyle(Notification.BigTextStyle().bigText(message.data["body"]))
                .setContentIntent(pending).setAutoCancel(true).build()
            if(session==null&&lanSession!=null)lanRepository.ifCurrent(lanSession){if(Api.prefs(this).getString("push_route","none")=="local")manager.notify("local:${lanSession.generation}:$delivery",0,notification)}
            else if(session!=null)repository.ifCurrentNotification(session){if(Api.prefs(this).getString("push_route","none")=="cloud")manager.notify(delivery,0,notification)}
        }
        Thread { Api.flushReceipts(this) }.start()
    }
}
