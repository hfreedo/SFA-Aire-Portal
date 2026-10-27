package org.sfa.aire

import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Switch
import org.json.JSONObject
import org.sfa.aire.ui.WorkspaceLayout
import org.sfa.aire.ui.AireUi
import org.sfa.aire.ui.screens.SettingsScreen
import org.sfa.aire.ui.screens.SettingsState
import java.time.Instant

/** Vistas reales, datos ficticios y callbacks sin red; no acredita registro ni FCM reales. */
class VisualRefinementChecks(private val instrumentation:Instrumentation){
 private fun nodes():List<AccessibilityNodeInfo>{
  val result=mutableListOf<AccessibilityNodeInfo>()
  fun visit(n:AccessibilityNodeInfo){result.add(n);for(i in 0 until n.childCount)n.getChild(i)?.let{visit(it)}}
  instrumentation.uiAutomation.rootInActiveWindow?.let{visit(it)};return result
 }
 fun verify(){
  val monitor=instrumentation.addMonitor("org.sfa.aire.CloudActivity",null,false)
  instrumentation.targetContext.startActivity(Intent(instrumentation.targetContext,CloudActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("demo",true))
  val activity=instrumentation.waitForMonitorWithTimeout(monitor,10000)?:error("Demo did not launch")
  instrumentation.removeMonitor(monitor);instrumentation.waitForIdleSync()
  fun capture(name:String){
   instrumentation.waitForIdleSync();SystemClock.sleep(250)
   instrumentation.uiAutomation.takeScreenshot().let{bitmap->java.io.FileOutputStream(java.io.File(activity.cacheDir,name+".png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()}
  }
  try{
   val layout=CloudActivity::class.java.getDeclaredField("layout").apply{isAccessible=true}.get(activity) as WorkspaceLayout
   val overview=CloudActivity::class.java.getDeclaredField("overview").apply{isAccessible=true}.get(activity) as JSONObject
   val update=CloudActivity::class.java.getDeclaredMethod("applyOverview",JSONObject::class.java).apply{isAccessible=true}
   val first=layout.root.getChildAt(0)
   capture("v073-aula")
   instrumentation.runOnMainSync{
    overview.getJSONArray("snapshots").getJSONObject(0).getJSONObject("observation").put("temperature",29)
    update.invoke(activity,overview)
    check(layout.root.getChildAt(0)===first){"Telemetry rebuilt the screen"}
   }
   instrumentation.waitForIdleSync()
   check(nodes().any{it.text?.toString()?.startsWith("29")==true})
   instrumentation.runOnMainSync{
    overview.getJSONArray("snapshots").getJSONObject(0).put("sample_at",Instant.now().minusSeconds(57399).toString())
    update.invoke(activity,overview)
    check(layout.root.getChildAt(0)===first)
   }
   instrumentation.waitForIdleSync()
   check(nodes().any{it.text?.toString()=="LECTURA VENCIDA"})
   check(nodes().any{it.text?.toString()?.contains("15 horas")==true||it.text?.toString()?.contains("16 horas")==true})
   capture("v073-vencida")
   var settingsRoot:LinearLayout?=null;var ui:AireUi?=null;var calls=0;var consent=false
   instrumentation.runOnMainSync{
    val root=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL;setPadding(24,24,24,24)};settingsRoot=root
    activity.setContentView(ScrollView(activity).apply{addView(root)})
    ui=AireUi(activity,root,{false},{false})
    SettingsScreen(ui!!).render(SettingsState(false,"docente@example.test",true,false,false,true,"Aula de ejemplo"),{calls++;consent=it},{},{},{},{},{})
   }
   instrumentation.waitForIdleSync();check(nodes().any{it.text?.toString()=="AVISOS ACTIVOS"})
   capture("v073-registro-confirmado-fixture")
   instrumentation.runOnMainSync{
    fun find(view:android.view.View):Switch?{if(view is Switch)return view;if(view is android.view.ViewGroup)for(i in 0 until view.childCount)find(view.getChildAt(i))?.let{return it};return null}
    find(settingsRoot!!)!!.isChecked=true
    check(calls==0){"Changing the switch submitted a cloud action"}
   }
   instrumentation.waitForIdleSync()
   val save=nodes().first{it.text?.toString()=="Guardar preferencia"&&it.isClickable}
   check(save.performAction(AccessibilityNodeInfo.ACTION_CLICK));instrumentation.waitForIdleSync()
   check(calls==1&&consent)
   val details=nodes().first{it.text?.toString()?.startsWith("Detalles del registro")==true&&it.isClickable}
   check(details.performAction(AccessibilityNodeInfo.ACTION_CLICK));SystemClock.sleep(250)
   instrumentation.waitForIdleSync();check(ui!!.disclosures["notification-details"]==true)
   capture("v073-detalles-registro-fixture")
  }finally{instrumentation.runOnMainSync{activity.finish()}}
 }
}
