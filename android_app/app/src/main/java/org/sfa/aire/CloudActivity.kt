package org.sfa.aire

import org.sfa.aire.application.WorkspaceActions
import org.sfa.aire.application.WorkspaceResult
import org.sfa.aire.application.CareCommands
import org.sfa.aire.application.CareCommand
import org.sfa.aire.ui.screens.AccessScreen
import org.sfa.aire.ui.WorkspaceLayout
import org.sfa.aire.application.RequestScope
import org.sfa.aire.data.session.SessionRepository
import org.sfa.aire.data.demo.DemoWorkspace
import org.sfa.aire.ui.CareDialogs
import org.sfa.aire.ui.screens.ClassroomScreen
import org.sfa.aire.ui.screens.IncidentsScreen
import org.sfa.aire.ui.screens.SettingsScreen
import org.sfa.aire.ui.screens.SettingsState

import android.Manifest
import android.app.Activity
import android.app.NotificationManager
import android.content.Intent
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.*
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import org.json.JSONObject
import java.util.concurrent.Executors

class CloudActivity:Activity() {
    private val actions by lazy{WorkspaceActions(applicationContext)}
    private lateinit var layout:WorkspaceLayout
    private val ui get()=layout.ui
    private val root get()=layout.root
    private val status get()=layout.status
    private val nav get()=layout.nav
    private val scroll get()=layout.scroll
    private val requestScope=RequestScope()
    private var pendingPushConsent=false
    private val io=Executors.newSingleThreadExecutor()
    private val handler=Handler(Looper.getMainLooper())
    private lateinit var dialogs:CareDialogs
    private var active=false
    private var busy=false
    private var demoMode=false
    private var verified=false
    private var verifiedGeneration:Long?=null
    private var page="aula"
    private var overview:JSONObject?=null
    private val freshnessUpdates=mutableListOf<()->Unit>()
    private val dataUpdates=mutableListOf<(JSONObject)->Unit>()
    private val scrollPositions=mutableMapOf<String,Int>()
    private var renderedKey:String?=null
    private var animateAfterSave=false
    private var navigating=false
    private val freshnessClock=object:Runnable{override fun run(){if(active){freshnessUpdates.toList().forEach{it()};handler.postDelayed(this,10000)}}}
    private val poll=object:Runnable{override fun run(){if(active&&!demoMode){refresh();handler.postDelayed(this,60000)}}}
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        demoMode=intent.getBooleanExtra("demo",false)
        layout=WorkspaceLayout(this,{demoMode},{busy})
        dialogs=CareDialogs(ui,{verified&&!demoMode&&verifiedGeneration==SessionRepository(this).generation()},{busy||demoMode})
        handleOpen(intent)
        if(demoMode){overview=DemoWorkspace.load(this);verified=true;render(overview!!)}
        else if(!CloudApi.hasSession(this))showLogin() else {text(root,"Cargando sus aulas…",20f,true);refresh()}
    }
    private fun text(parent:LinearLayout,value:String,size:Float=15f,bold:Boolean=false)=ui.text(parent,value,size,bold)
    private fun button(parent:LinearLayout,title:String,action:()->Unit)=ui.button(parent,title,action)
    private fun secondary(parent:LinearLayout,title:String,action:()->Unit)=ui.secondary(parent,title,action)
    private fun card(parent:LinearLayout=root,color:Int=Color.WHITE)=ui.card(parent,color)
    private fun goToPage(id:String){
        if(id==page||navigating||busy)return
        val tabs=listOf("aula","incidentes","ajustes")
        val direction=if(tabs.indexOf(id)>tabs.indexOf(page))1 else -1
        scrollPositions[page]=scroll.scrollY;navigating=true
        layout.transition(direction,{
            page=id;overview?.let{render(it)}
            scroll.post{scroll.scrollTo(0,scrollPositions[id]?:0)}
        },{navigating=false})
    }
    private fun navigation()=layout.navigation(page,{goToPage(it)})
    private fun invalidateUi(){requestScope.invalidate();verifiedGeneration=null;busy=false;dialogs.dismiss()}
    private fun showLogin(){
        invalidateUi()
        root.removeAllViews();freshnessUpdates.clear();dataUpdates.clear();renderedKey=null;nav.visibility=View.GONE
        AccessScreen(ui).render(actions.connection().configured,Api.prefs(this).getString("cloud_email","")!!,
            {email,password->network{actions.login(email,password)}},
            {invalidateUi();demoMode=true;verified=true;overview=DemoWorkspace.load(this);status.text="DEMOSTRACIÓN · Datos ficticios · Sin envíos";render(overview!!)},
            {startActivity(Intent(this,MainActivity::class.java))})
    }
    private fun network(work:()->WorkspaceResult){
        if(busy||demoMode)return;busy=true;status.text="Actualizando…"
        val ticket=requestScope.capture()
        io.execute{
            try{val result=work();Api.flushReceipts(this);runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){if(result.generation!=SessionRepository(this).generation()){busy=false;verified=false;verifiedGeneration=null;showLogin();status.text="La sesión cambió. Verifique su acceso.";return@runOnUiThread};overview=result.data;verified=true;verifiedGeneration=result.generation;busy=false;applyOverview(result.data);status.text="Consulta actualizada · "+java.text.DateFormat.getTimeInstance(java.text.DateFormat.SHORT).format(java.util.Date())}}}
            catch(e:Exception){runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){verified=false;busy=false;status.text="Sin estado remoto verificable: ${e.message}";root.removeAllViews();freshnessUpdates.clear();dataUpdates.clear();renderedKey=null;val box=card();text(box,"No se pudo actualizar",23f,true);text(box,"Revise su conexión. Las acciones de atención permanecen bloqueadas hasta recuperar un estado verificable.");button(box,"Reintentar"){refresh()};secondary(box,"Volver al acceso"){showLogin()}}}}
        }
    }
    private fun refresh(){if(!demoMode&&CloudApi.hasSession(this))network{actions.refresh()}}
    private fun notificationsPermitted():Boolean {
        val notifications=getSystemService(NotificationManager::class.java)
        return notifications.getNotificationChannel("aula_alerts")?.importance!=NotificationManager.IMPORTANCE_NONE&&notifications.areNotificationsEnabled()&&(Build.VERSION.SDK_INT<33||checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)==android.content.pm.PackageManager.PERMISSION_GRANTED)
    }
    private fun presentationKey(data:JSONObject):String {
        val p=Api.prefs(this);val room=p.getString("cloud_room","").orEmpty()
        val base=page+"|"+room+"|"+verifiedGeneration+"|"+data.optJSONArray("classrooms")+"|"+data.optJSONArray("memberships")
        if(page=="ajustes")return base+"|"+notificationsPermitted()+"|"+actions.notificationRegistered(room)+"|"+p.getBoolean("cloud_simulations",false)+"|"+p.getBoolean("receipts_overflow",false)
        val snapshots=data.optJSONArray("snapshots")
        val identities=(0 until (snapshots?.length()?:0)).joinToString("|"){val s=snapshots!!.getJSONObject(it);s.optString("classroom_id")+":"+s.optString("gateway_id")}
        return base+"|"+identities+"|"+data.optJSONArray("incidents")+"|"+data.optJSONArray("deliveries")
    }
    private fun applyOverview(data:JSONObject){
        if(renderedKey==presentationKey(data)){
            if(page=="aula"&&dataUpdates.isNotEmpty()){dataUpdates.toList().forEach{it(data)};return}
            if(page=="ajustes")return
        }
        val y=if(renderedKey==null)0 else scroll.scrollY
        val animate=animateAfterSave;animateAfterSave=false
        render(data);scroll.post{scroll.scrollTo(0,y);if(animate)ui.enter(root)}
    }
    private fun settings(){
        val p=Api.prefs(this)
        val permitted=notificationsPermitted()
        val roomId=p.getString("cloud_room","").orEmpty()
        val rooms=overview?.optJSONArray("classrooms")
        val roomName=if(demoMode)"Aula de ejemplo" else (0 until (rooms?.length()?:0)).map{rooms!!.getJSONObject(it)}.firstOrNull{it.optString("id")==roomId}?.optString("name")?:"Sin aula seleccionada"
        SettingsScreen(ui).render(SettingsState(demoMode,p.getString("cloud_email","")!!,permitted,p.getBoolean("cloud_simulations",false),p.getBoolean("receipts_overflow",false),actions.notificationRegistered(roomId),roomName,
            p.getString("cloud_push_room",null)?.takeIf{actions.notificationRegistered(it)}?.let{bound->
                (0 until (rooms?.length()?:0)).map{rooms!!.getJSONObject(it)}.firstOrNull{it.optString("id")==bound}?.optString("name")?:"otra aula"
            }),
            {registerPush(it)},
            {startActivity(Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(android.provider.Settings.EXTRA_APP_PACKAGE,packageName))},
            {refresh()},
            {startActivity(Intent(this,MainActivity::class.java).putExtra("local",true))},
            {logout()},
            {demoMode=false;overview=null;verified=false;page="aula";showLogin()})
    }
    private fun logout(){
        if(busy||demoMode)return
        busy=true
        val ticket=requestScope.capture()
        io.execute{
            try{val unlinked=actions.logout();runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){overview=null;busy=false;verified=false;showLogin();status.text=if(unlinked)"Sesión cerrada y teléfono desvinculado" else "Sesión cerrada. Falta desvincular el teléfono en la nube; contacte al administrador."}}}
            catch(e:Exception){runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){busy=false;status.text="No se pudo completar el cierre local: ${e.message}"}}}
        }
    }
    private fun render(data:JSONObject){
        val firstWorkspace=renderedKey==null
        root.animate().cancel();root.alpha=1f;root.translationY=0f
        root.removeAllViews();freshnessUpdates.clear();dataUpdates.clear();navigation()
        renderedKey=presentationKey(data)
        if(firstWorkspace)scroll.post{scroll.scrollTo(0,0)}
        if(page=="ajustes"){settings();return}
        if(page=="incidentes"){text(root,"Avisos",22f,true);ui.space(height=8)}
        val rooms=data.getJSONArray("classrooms")
        if(rooms.length()==0){val box=card();text(box,"Todavía no hay aulas",23f,true);text(box,"Pida al responsable que vincule su cuenta. Puede revisar su sesión en Ajustes.");return}
        val p=Api.prefs(this);val list=(0 until rooms.length()).map{rooms.getJSONObject(it)}
        val selected=if(demoMode)list[0] else list.firstOrNull{it.getString("id")==p.getString("cloud_room",null)}?:list[0]
        val roomId=selected.getString("id");if(!demoMode)p.edit().putString("cloud_room",roomId).apply()
        renderedKey=presentationKey(data)
        if(list.size>1&&!demoMode){
            secondary(root,selected.getString("name")){
                ui.choose("Selecciona un aula",list.map{it.getString("name")},list.indexOf(selected)){index->
                    if(!busy){p.edit().putString("cloud_room",list[index].getString("id")).apply();render(data);scroll.post{scroll.scrollTo(0,0)};ui.enter(root)}
                }
            }.apply{textSize=18f;gravity=android.view.Gravity.START or android.view.Gravity.CENTER_VERTICAL;contentDescription="Seleccionar aula. "+selected.getString("name");ui.surface(this,Color.WHITE);background=android.graphics.drawable.RippleDrawable(android.content.res.ColorStateList.valueOf(ui.sage),ui.shape(Color.WHITE,ui.sageStrong),ui.shape(Color.WHITE));setCompoundDrawablesWithIntrinsicBounds(null,null,org.sfa.aire.ui.AireIcon(this@CloudActivity,"chevron",ui.green,22),null);compoundDrawablePadding=ui.dp(10)}
        } else text(root,selected.getString("name"),if(page=="incidentes")16f else 22f,true)
        selected.optString("school").takeIf{it.isNotBlank()}?.let{text(root,it,14f).setPadding(0,0,0,ui.dp(10))}
        val all=data.getJSONArray("incidents");val incidents=(0 until all.length()).map{all.getJSONObject(it)}.filter{it.getString("classroom_id")==roomId}
        if(page=="aula"){
            ClassroomScreen(ui).render(data,roomId,incidents,freshnessUpdates,{goToPage("incidentes")},{refresh()},dataUpdates)
            return
        }
        IncidentsScreen(ui,::closeNotice,verified&&verifiedGeneration==SessionRepository(this).generation(),::shareNotice,::commentNotice).render(data,incidents)
    }

    private fun change(command:CareCommand) {
        if(demoMode||!verified||busy)return
        val generation=verifiedGeneration
        if(generation==null||generation!=SessionRepository(this).generation()){status.text="La sesión cambió. Actualice el aula antes de actuar.";return}
        if(!dialogs.isOpen){network{actions.execute(command,generation);actions.refresh()};return}
        busy=true;dialogs.saving(true)
        val ticket=requestScope.capture()
        io.execute{
            try{
                actions.execute(command,generation)
                runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){busy=false;dialogs.dismiss();animateAfterSave=true;status.text="Registro guardado. Actualizando estado…";refresh()}}
            }catch(e:Exception){runOnUiThread{if(!isDestroyed&&requestScope.accepts(ticket)){busy=false;dialogs.failure(e.message?:"Error de conexión")}}}
        }
    }
    private fun closeNotice(item:JSONObject){change(CareCommands.attention(item,"resolver",""))}
    private fun commentNotice(item:JSONObject){
        dialogs.note("Marcar aviso como atendido","Esto cierra el aviso, sin modificar la medición del sensor.",optional=true){change(CareCommands.attention(item,"resolver",it))}
    }
    private fun shareNotice(item:JSONObject){
        val message="SFA Aire · "+(if(item.optString("source")=="simulacion")"SIMULACIÓN" else "Aviso ambiental")+" · Revisar el ambiente del aula. "+item.optString("opened_at")+" "+item.optString("note")
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply{type="text/plain";putExtra(Intent.EXTRA_TEXT,message)},"Compartir aviso"))
    }
    private fun registerPush(acceptSimulations:Boolean=pendingPushConsent) {
        pendingPushConsent=acceptSimulations
        if(demoMode)return
        if(!CloudApi.hasSession(this)){status.text="Inicie sesión y seleccione un aula";return}
        if(verifiedGeneration!=SessionRepository(this).generation()){status.text="Actualice el aula antes de registrar el teléfono";return}
        if(Build.VERSION.SDK_INT>=33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=android.content.pm.PackageManager.PERMISSION_GRANTED){requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS),2);return}
        if(FirebaseApp.getApps(this).isEmpty()){status.text="La APK no incluye google-services.json. Recompile con Firebase para activar FCM.";return}
        if(busy)return
        val ticket=requestScope.capture()
        val generation=SessionRepository(this).generation()
        busy=true;status.text="Preparando registro de notificaciones…"
        val timeout=Runnable{if(!isDestroyed&&requestScope.accepts(ticket)&&busy){invalidateUi();status.text="El registro tardó demasiado. Revise la conexión y vuelva a intentar."}}
        handler.postDelayed(timeout,15000)
        FirebaseMessaging.getInstance().token.addOnCompleteListener{task->
            handler.removeCallbacks(timeout)
            if(isDestroyed||!requestScope.accepts(ticket))return@addOnCompleteListener
            busy=false
            if(task.isSuccessful)network{actions.registerPhone(task.result,acceptSimulations,generation)}
            else status.text="No se pudo obtener el token FCM"
        }
    }

    private fun handleOpen(intent:Intent){
        val delivery=intent.getStringExtra("delivery_id")?:return
        intent.removeExtra("delivery_id")
        val session=org.sfa.aire.data.notifications.NotificationSession(intent.getLongExtra("notification_generation",-1),intent.getStringExtra("notification_binding").orEmpty())
        if(Api.prefs(this).getString("push_route","none")!="cloud")return
        val repository=SessionRepository(this)
        val accepted=repository.ifCurrentNotification(session){
            invalidateUi()
            intent.getStringExtra("classroom_id")?.let{room->try{java.util.UUID.fromString(room);Api.prefs(this).edit().putString("cloud_room",room).apply()}catch(_:Exception){}}
            page="incidentes"
            renderedKey=null;scrollPositions["incidentes"]=0
        }
        if(accepted)Api.enqueueReceipt(this,delivery,"abierto","cloud",session.generation)
    }
    override fun onRequestPermissionsResult(requestCode:Int,permissions:Array<out String>,results:IntArray){super.onRequestPermissionsResult(requestCode,permissions,results);if(requestCode==2){if(results.firstOrNull()==android.content.pm.PackageManager.PERMISSION_GRANTED)registerPush() else status.text="Permiso de notificaciones pendiente. Puede revisar las mediciones sin push."}}
    override fun onNewIntent(intent:Intent){super.onNewIntent(intent);handleOpen(intent);refresh()}
    override fun onResume(){super.onResume();active=true;handler.post(poll);handler.post(freshnessClock)}
    override fun onPause(){active=false;handler.removeCallbacks(poll);handler.removeCallbacks(freshnessClock);layout.cancelTransition();navigating=false;super.onPause()}
    override fun onDestroy(){requestScope.invalidate();dialogs.dismiss();io.shutdown();super.onDestroy()}
}
