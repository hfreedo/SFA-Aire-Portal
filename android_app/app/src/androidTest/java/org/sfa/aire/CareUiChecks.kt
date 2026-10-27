package org.sfa.aire
import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.os.Bundle
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import org.sfa.aire.ui.AireUi
import org.sfa.aire.ui.CareDialogs
import org.sfa.aire.ui.screens.SettingsScreen
import org.sfa.aire.ui.screens.SettingsState
import org.sfa.aire.ui.screens.IncidentsScreen
import org.sfa.aire.ui.screens.CoordinationScreen
import org.sfa.aire.ui.screens.CoordinationEvents
import org.sfa.aire.data.demo.DemoWorkspace
import org.json.JSONObject
import java.util.concurrent.atomic.AtomicReference

/** Prueba de formularios reales con callbacks ficticios; no ejecuta casos de uso cloud. */
class CareUiChecks(private val instrumentation:Instrumentation){
 private fun all():List<AccessibilityNodeInfo>{
    val result=mutableListOf<AccessibilityNodeInfo>()
    fun visit(node:AccessibilityNodeInfo){result.add(node);for(index in 0 until node.childCount)node.getChild(index)?.let{visit(it)}}
    instrumentation.uiAutomation.rootInActiveWindow?.let{visit(it)}
    return result
 }
 private fun fields():List<AccessibilityNodeInfo>{
    repeat(30){val nodes=all().filter{it.className=="android.widget.EditText"};if(nodes.isNotEmpty())return nodes;SystemClock.sleep(100)}
    error("Input not visible")
 }
 private fun write(index:Int,text:String){check(fields()[index].performAction(AccessibilityNodeInfo.ACTION_SET_TEXT,Bundle().apply{putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,text)}));instrumentation.waitForIdleSync()}
 private fun click(label:String){val node=all().firstOrNull{(it.text?.toString()?.equals(label,ignoreCase=true)==true||it.contentDescription?.toString()?.equals(label,ignoreCase=true)==true)&&it.isClickable}?:error("Button not visible: $label");check(node.performAction(AccessibilityNodeInfo.ACTION_CLICK));instrumentation.waitForIdleSync();SystemClock.sleep(150)}
 fun verify(){
    var activity:Activity?=null;var dialogs:CareDialogs?=null;var stage="launch"
    try{
        val monitor=instrumentation.addMonitor("org.sfa.aire.CloudActivity",null,false)
        instrumentation.targetContext.startActivity(Intent(instrumentation.targetContext,CloudActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("demo",true))
        activity=instrumentation.waitForMonitorWithTimeout(monitor,10000)?:error("Demo activity did not open")
        instrumentation.removeMonitor(monitor);instrumentation.waitForIdleSync()
        val current=activity
        fun capture(name:String){instrumentation.waitForIdleSync();SystemClock.sleep(500);instrumentation.uiAutomation.takeScreenshot().let{bitmap->java.io.FileOutputStream(java.io.File(current.cacheDir,name+".png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()}}
        capture("v071-aula")
        stage="sensor information"
        repeat(8){
            if(all().none{node->node.text?.toString()=="Información de sensores"||node.contentDescription?.toString()=="Información de sensores"}){
                all().firstOrNull{node->node.className=="android.widget.ScrollView"}?.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD)
                instrumentation.waitForIdleSync();SystemClock.sleep(100)
            }
        }
        click("Información de sensores");capture("v071-sensores")
        check(all().any{it.text?.toString()=="Temperatura · DHT"})
        click("Entendido")
        click("Avisos");capture("v071-avisos")
        click("Ajustes");capture("v071-ajustes")
        click("Mi aula")
        instrumentation.runOnMainSync{dialogs=CareDialogs(AireUi(current,LinearLayout(current),{false},{false}),{true},{false})}
        val received=AtomicReference<String?>()
        stage="note validation"
        instrumentation.runOnMainSync{dialogs!!.note("Atención de prueba","Observación de prueba"){value->received.set(value);dialogs!!.saving(true);dialogs!!.failure("Rechazo simulado del servidor")}}
        fields();write(0,"x");click("Guardar");check(received.get()==null)
        stage="note preservation"
        write(0,"Observación conservada de prueba");click("Guardar")
        check(received.get()=="Observación conservada de prueba")
        check(fields()[0].text.toString()=="Observación conservada de prueba")
        click("Cancelar");instrumentation.runOnMainSync{check(!dialogs!!.isOpen)}
        stage="optional attention note"
        received.set(null)
        instrumentation.runOnMainSync{dialogs!!.note("Marcar aviso como atendido","Nota opcional",optional=true){value->received.set(value)}}
        fields();SystemClock.sleep(400)
        instrumentation.uiAutomation.takeScreenshot().let{bitmap->
            java.io.FileOutputStream(java.io.File(current.cacheDir,"atencion-simple-formulario.png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
            bitmap.recycle()
        }
        click("Guardar");check(received.get()=="")
        instrumentation.runOnMainSync{dialogs!!.dismiss()}
        stage="instruction validation"
        val emitted=AtomicReference<String?>()
        instrumentation.runOnMainSync{dialogs!!.instruction("stable-fixture"){_,_,_,id->emitted.set(id)}}
        fields();write(0,"Ventilar el aula");write(1,"Variación comprobada");write(2,"121");click("Emitir");check(emitted.get()==null)
        write(2,"30");click("Emitir");check(emitted.get()=="stable-fixture")
        instrumentation.runOnMainSync{dialogs!!.dismiss()}
        stage="notification registration notice"
        instrumentation.runOnMainSync{
            val root=LinearLayout(current).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
            current.setContentView(android.widget.ScrollView(current).apply{addView(root)})
            SettingsScreen(AireUi(current,root,{false},{false})).render(
                SettingsState(false,"cuenta@example.test",true,false,false,false),{},{},{},{},{},{})
        }
        instrumentation.waitForIdleSync()
        check(all().any{it.text?.toString()?.contains("Registro pendiente para esta sesión y aula")==true})
        instrumentation.uiAutomation.takeScreenshot().let{bitmap->
            java.io.FileOutputStream(java.io.File(current.cacheDir,"notification-settings.png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
            bitmap.recycle()
        }
        stage="direct attendance without compulsory dialog"
        var attended=0;var commented=0
        instrumentation.runOnMainSync{
            val root=LinearLayout(current).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
            current.setContentView(android.widget.ScrollView(current).apply{addView(root)})
            val data=DemoWorkspace.load(current)
            val item=data.getJSONArray("incidents").getJSONObject(0).put("capabilities",JSONObject().put("can_resolve",true))
            IncidentsScreen(AireUi(current,root,{false},{false}),{attended++},true,{}, {commented++}).render(data,listOf(item))
        }
        instrumentation.waitForIdleSync();click("Marcar atendido")
        check(attended==1&&commented==0)
        check(all().none{it.className=="android.widget.EditText"}){"Attendance required a note"}
        click("Atender con nota");check(commented==1&&attended==1)
        stage="administrative archive label"
        instrumentation.runOnMainSync{
            val root=LinearLayout(current).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)}
            current.setContentView(android.widget.ScrollView(current).apply{addView(root)})
            val ui=AireUi(current,root,{false},{false})
            val data=DemoWorkspace.load(current)
            val item=data.getJSONArray("incidents").getJSONObject(0).put("status","resuelto")
                .put("closure_kind","administrativo").put("closure_reason","Receptor retirado durante ensayo de demostración")
                .put("note","ARCHIVO ADMINISTRATIVO · No confirma normalización. Motivo: receptor retirado")
            IncidentsScreen(ui,{error("Unexpected attention command")},false,{}).render(data,listOf(item))
        }
        instrumentation.waitForIdleSync()
        check(all().any{it.text?.toString()=="Aviso atendido"})
        check(all().none{it.text?.toString()=="Resuelto"})
        instrumentation.uiAutomation.takeScreenshot().let{bitmap->
            java.io.FileOutputStream(java.io.File(current.cacheDir,"administrative-archive.png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)}
            bitmap.recycle()
        }
    }catch(error:Throwable){throw IllegalStateException("Care UI failed at $stage: ${error.javaClass.simpleName} / ${error.message}",error)}
    finally{instrumentation.runOnMainSync{dialogs?.dismiss();activity?.finish()}}
 }
}
