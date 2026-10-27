package org.sfa.aire

import org.sfa.aire.ui.AireUi
import org.sfa.aire.ui.CareDialogs
import org.sfa.aire.application.RequestScope
import org.sfa.aire.data.session.LanConnectionRepository
import org.sfa.aire.data.session.LanSession
import org.sfa.aire.data.notifications.LocalNotificationPolicy
import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.app.NotificationManager
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.View
import android.widget.*
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var ui:AireUi
    private lateinit var dialogs:CareDialogs
    private val requestScope=RequestScope()
    private var savedServer=""
    private var displayedGeneration=0L
    private var verified=false
    private var verifiedLan:LanSession?=null
    private var attentionSaving=false
    private lateinit var content: LinearLayout
    private lateinit var status: TextView
    private lateinit var measurements: TextView
    private lateinit var incidents: LinearLayout
    private lateinit var server: EditText
    private lateinit var key: EditText
    private lateinit var simulations: CheckBox
    private lateinit var pushStatus: TextView
    private val handler = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private var active = false
    private var fetching = false
    private val poll = object : Runnable {
        override fun run() { if (active) { refresh(); handler.postDelayed(this, 3000) } }
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val scroll = ScrollView(this)
        content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(28, 28, 28, 28); setBackgroundColor(Color.rgb(244,246,242)) }
        ui=AireUi(this,content,{false},{attentionSaving})
        dialogs=CareDialogs(ui,{verified},{attentionSaving})
        content.setPadding(ui.dp(18),ui.dp(18),ui.dp(18),ui.dp(24))
        scroll.addView(content); setContentView(scroll)
        scroll.setOnApplyWindowInsetsListener { v, insets ->
            if (Build.VERSION.SDK_INT >= 30) {
                val bars = insets.getInsets(android.view.WindowInsets.Type.systemBars())
                v.setPadding(0, bars.top, 0, bars.bottom)
            }
            insets
        }
        text("SFA  Aire", 30f, true)
        button("Acceso remoto · Mis aulas") { startActivity(Intent(this, CloudActivity::class.java)) }
        text("MONITOREO LOCAL · AULA SIN IDENTIDAD VERIFICADA", 11f)
        status = text("Conecte la app con la PC de la maqueta.", 20f, true)
        measurements = text("Sin mediciones recientes.", 17f)
        button("Actualizar") { refresh() }
        text("Incidentes y atención", 23f, true)
        incidents = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }; content.addView(incidents)
        text("Conexión con la PC", 23f, true)
        text("Use la misma red Wi-Fi. Inicie iniciar_red_local.bat en la PC. Por internet use una URL HTTPS válida.", 13f)
        val connection=try { LanConnectionRepository(this).read() }catch(e:Exception){status.text=e.message;null}
        savedServer=connection?.server.orEmpty()
        displayedGeneration=LanConnectionRepository(this).generation()
        server = input("URL de la PC, ej. http://192.168.1.20:8766", savedServer)
        key = input("Clave de conexión de la PC", connection?.key.orEmpty()).apply { inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD }
        simulations = CheckBox(this).apply { text = "Recibir push de SIMULACIÓN"; isChecked = Api.prefs(this@MainActivity).getBoolean("simulations", false) }; content.addView(simulations)
        button("Guardar y conectar") {
            val old = savedServer
            if (old != server.text.toString().trim().trimEnd('/') && Api.prefs(this).getString("fcm_token", null) != null) {
                AlertDialog.Builder(this).setMessage("Antes de cambiar de PC, desvincule este teléfono en el panel anterior para que deje de recibir sus alertas.").setPositiveButton("Continuar") { _, _ -> if(save())refresh() }.setNegativeButton("Cancelar", null).show()
            } else { if(save())refresh() }
        }
        text("Notificaciones push", 23f, true)
        pushStatus = text(if (FirebaseApp.getApps(this).isEmpty()) "Esta APK no tiene configuración Firebase. Puede consultar la PC. Agregue google-services.json y recompile para activar FCM." else "Firebase disponible. Registre este teléfono.", 13f)
        button("Registrar / actualizar push") { registerPush() }
        text("Recibido indica llegada a la app; abierto indica apertura del aviso. La atención es independiente de la medición.", 12f)
        text("Prototipo educativo · MQ135 relativo, sin ppm. El DHT mide temperatura y humedad.", 12f)
        handleOpen(intent)
    }
    private fun save():Boolean {
        val repository=LanConnectionRepository(this)
        val previous=repository.generation()
        val connection=try { repository.save(server.text.toString().trim(),key.text.toString().trim()) }catch(e:Exception){status.text=e.message;return false}
        invalidateConnectionView("LOCAL · Verificando conexión con la PC")
        displayedGeneration=repository.generation()
        if(previous!=repository.generation()){pushStatus.text="Registro de avisos pendiente para esta conexión."}
        if(previous!=repository.generation())getSystemService(NotificationManager::class.java).let{manager->
            manager.activeNotifications.filter{it.tag?.startsWith("local:$previous:")==true}.forEach{manager.cancel(it.tag,it.id)}
        }
        savedServer=connection.server
        Api.prefs(this).edit().putBoolean("simulations", simulations.isChecked).apply()
        return true
    }
    private fun invalidateConnectionView(message:String){
        requestScope.invalidate();verified=false;verifiedLan=null;fetching=false;attentionSaving=false;dialogs.dismiss()
        status.text=message
        measurements.text="Sin mediciones verificadas para esta conexión."
        incidents.removeAllViews()
    }
    private fun syncConnection(){
        val repository=LanConnectionRepository(this)
        if(repository.generation()==displayedGeneration)return
        val connection=try{repository.read()}catch(_:Exception){null}
        displayedGeneration=repository.generation();savedServer=connection?.server.orEmpty()
        server.setText(savedServer);key.setText(connection?.key.orEmpty())
        invalidateConnectionView("LOCAL · La conexión cambió; verifique la PC")
        pushStatus.text="Revise el registro de avisos para esta conexión."
    }
    private fun registerPush() {
        if(!save())return
        Api.prefs(this).edit().putString("push_route","local").apply()
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        if (FirebaseApp.getApps(this).isEmpty()) { pushStatus.text = "Falta google-services.json en la compilación. Consulte docs/INTEGRACION.md."; return }
        val ticket=requestScope.capture()
        val session=LanConnectionRepository(this).snapshot()?:return
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if(isDestroyed||!requestScope.accepts(ticket)||!LanConnectionRepository(this).isCurrent(session))return@addOnCompleteListener
            if (!task.isSuccessful) { pushStatus.text = "No se pudo obtener el token FCM: ${task.exception?.javaClass?.simpleName}"; return@addOnCompleteListener }
            io.execute {
                try {
                    Api.register(this, task.result,session)
                    runOnUiThread { if(!isDestroyed&&requestScope.accepts(ticket)&&LanConnectionRepository(this).isCurrent(session))pushStatus.text = "Teléfono registrado. Permiso del sistema: " + if (getSystemService(NotificationManager::class.java).areNotificationsEnabled()) "habilitado" else "deshabilitado" }
                } catch (e: Exception) { runOnUiThread { if(!isDestroyed&&requestScope.accepts(ticket))pushStatus.text = "No se pudo registrar: ${e.message}" } }
            }
        }
    }
    private fun text(value:String,size:Float,bold:Boolean=false)=ui.text(content,value,size,bold)
    private fun input(hintText:String,value:String)=ui.input(content,hintText,value)
    private fun button(title:String,action:()->Unit)=ui.button(content,title,action)
    private fun refresh() {
        if (fetching || attentionSaving || savedServer.isBlank()) return
        val session=try{LanConnectionRepository(this).snapshot()}catch(e:Exception){status.text=e.message;null}?:return
        fetching = true
        val ticket=requestScope.capture()
        io.execute {
            try {
                val data = Api.request(this, "/state",lanSession=session)
                Api.flushReceipts(this)
                runOnUiThread {
                    if(!isDestroyed&&requestScope.accepts(ticket)){
                        fetching=false
                        if(LanConnectionRepository(this).isCurrent(session)){verified=true;verifiedLan=LanConnectionRepository(this).snapshot();render(data)}
                        else syncConnection()
                    }
                }
            } catch (e: Exception) {
                runOnUiThread {
                    if(isDestroyed||!requestScope.accepts(ticket))return@runOnUiThread
                    verified=false;verifiedLan=null
                    status.text = "Sin conexión verificable con la PC"
                    measurements.text = "Las mediciones anteriores están desactualizadas. ${e.message}"
                    incidents.removeAllViews()
                    fetching = false
                }
            }
        }
    }
    private fun render(data: JSONObject) {
        val labels = mapOf("normal" to "Sin variación sostenida", "alerta" to "REVISAR VENTILACIÓN", "aviso" to "Variación sostenida", "sin_calibrar" to "Falta referencia del sensor", "calentando" to "Sensor en estabilización", "fallo_sensor" to "Revisar sensores", "sin_datos" to "Sin datos recientes", "detenido" to "Monitoreo detenido")
        val source = if (data.optString("source") == "simulacion") "SIMULACIÓN" else data.optString("source").uppercase()
        status.text = "$source · ${labels[data.optString("state")] ?: data.optString("state")}"
        val sample = data.optJSONObject("latest")
        measurements.text = if (sample == null) "Sin muestras." else "MQ135: ${sample.optInt("mq_raw")} ADC\nTemperatura: ${sample.opt("temperature")} °C · Humedad: ${sample.opt("humidity")} %\nAntigüedad: ${data.optDouble("age_s", 0.0).toInt()} s · Emisor FCM: ${data.optString("push")}"
        val connection=verifiedLan
        pushStatus.text=Api.prefs(this).getString("lan_push_rejected_reason",null)?:when{
            connection?.receiverId==null -> "Receptor sin identidad local v2 verificada. Actualice la PC para registrar avisos."
            connection.registered -> "Registro confirmado para esta conexión y receptor."
            else -> "Identidad del receptor verificada. Registre este teléfono para recibir avisos."
        }
        if(connection!=null&&Api.prefs(this).getLong("lan_rejected_receipt_generation",-1)==connection.generation)
            pushStatus.append("\nUn acuse anterior no pudo confirmarse. Revise el historial del receptor.")
        incidents.removeAllViews()
        val list = data.getJSONArray("incidents")
        if(list.length()==0)ui.text(incidents,"Sin incidentes registrados.")
        for (n in 0 until list.length()) {
            val item = list.getJSONObject(n)
            val archived=item.optString("closure_kind")=="administrativo"
            val incidentStatus=if(archived)"Archivado administrativamente · Sin normalización verificada" else if(item.getString("status")=="resuelto")"Aviso atendido · No confirma normalización" else item.getString("status")
            val box=ui.card(incidents,if(archived)Color.rgb(236,238,241)else if(item.optString("status")=="resuelto")Color.rgb(230,239,228)else Color.rgb(255,233,216))
            box.addView(TextView(this).apply { text = "${item.getString("source").uppercase()} · ${item.getString("severity").uppercase()}\n${DateFormat.getDateTimeInstance().format(Date(item.getDouble("opened").toLong()*1000))}\n${incidentStatus} · ${item.optString("note")}"; textSize = 15f })
            val deliveries = data.getJSONArray("deliveries")
            val statuses = (0 until deliveries.length()).map { deliveries.getJSONObject(it) }.filter { it.optString("incident_id") == item.getString("id") }.map { it.optString("status") }
            box.addView(TextView(this).apply { text = "Push: " + if(statuses.isEmpty()) "sin destinatarios" else statuses.joinToString(" · ") })
            if (item.getString("status") != "resuelto") for ((action,title) in listOf("resolver" to "Marcar atendido")) {
                ui.button(box,title){attention(item.getString("id"),action)}
            }
        }
    }
    private fun attention(id:String,action:String){
        dialogs.note("Marcar aviso como atendido","La nota es opcional. Esto no confirma normalización del ambiente.",optional=true){note->
            if(!verified||attentionSaving)return@note
            val session=verifiedLan?:return@note
            val ticket=requestScope.capture();attentionSaving=true;dialogs.saving(true)
            io.execute{
                try{
                    check(requestScope.accepts(ticket)){"La conexión cambió. Revise el incidente"}
                    Api.request(this,"/incidents/$id/attention","POST",JSONObject().put("action",action).put("note",note),session)
                    runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){attentionSaving=false;dialogs.dismiss();refresh()}}
                }catch(e:Exception){runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){attentionSaving=false;dialogs.failure(e.message?:"Error de conexión")}}}
            }
        }
    }
    private fun handleOpen(intent: Intent) {
        val delivery=intent.getStringExtra("delivery_id")?:return
        intent.removeExtra("delivery_id")
        val current=try{LanConnectionRepository(this).snapshot()}catch(_:Exception){null}?:return
        val payload=mapOf("channel" to "local","local_contract" to "2","receiver_id" to intent.getStringExtra("local_receiver_id").orEmpty(),
            "notification_binding" to intent.getStringExtra("local_notification_binding").orEmpty(),"delivery_id" to delivery)
        if(Api.prefs(this).getString("push_route","none")!="local"||intent.getLongExtra("lan_generation",-1)!=current.generation||!LocalNotificationPolicy.accepts(payload,current))return
        Api.enqueueReceipt(this,delivery,"abierto","local",current.generation,current)
    }
    override fun onNewIntent(intent: Intent) { super.onNewIntent(intent); handleOpen(intent); refresh() }
    override fun onResume() { super.onResume();if(::ui.isInitialized){syncConnection();active=true;handler.post(poll)} }
    override fun onPause() { active = false; handler.removeCallbacks(poll); super.onPause() }
    override fun onDestroy() { requestScope.invalidate();if(::dialogs.isInitialized)dialogs.dismiss();io.shutdown(); super.onDestroy() }
}
