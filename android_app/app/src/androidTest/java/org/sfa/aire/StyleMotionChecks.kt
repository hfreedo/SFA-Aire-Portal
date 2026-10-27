package org.sfa.aire

import android.animation.ValueAnimator
import android.app.Activity
import android.app.Instrumentation
import android.content.Intent
import android.os.SystemClock
import android.view.accessibility.AccessibilityNodeInfo
import org.sfa.aire.ui.WorkspaceLayout

/** Componentes reales y fotogramas de propiedades animadas; sólo fixtures, sin red. */
class StyleMotionChecks(private val instrumentation:Instrumentation){
 private fun nodes():List<AccessibilityNodeInfo>{
  val result=mutableListOf<AccessibilityNodeInfo>()
  fun visit(n:AccessibilityNodeInfo){result.add(n);for(i in 0 until n.childCount)n.getChild(i)?.let{visit(it)}}
  instrumentation.uiAutomation.rootInActiveWindow?.let{visit(it)};return result
 }
 fun verify(){
  val monitor=instrumentation.addMonitor("org.sfa.aire.CloudActivity",null,false)
  instrumentation.targetContext.startActivity(Intent(instrumentation.targetContext,CloudActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK).putExtra("demo",true))
  val activity=instrumentation.waitForMonitorWithTimeout(monitor,10000)?:error("Demo did not launch")
  instrumentation.removeMonitor(monitor);instrumentation.waitForIdleSync();SystemClock.sleep(250)
  fun capture(name:String){instrumentation.waitForIdleSync();SystemClock.sleep(450);instrumentation.uiAutomation.takeScreenshot().let{bitmap->java.io.FileOutputStream(java.io.File(activity.cacheDir,name+".png")).use{bitmap.compress(android.graphics.Bitmap.CompressFormat.PNG,100,it)};bitmap.recycle()}}
  fun click(label:String){
   var node:AccessibilityNodeInfo?=null
   for(attempt in 0 until 30){node=nodes().firstOrNull{it.isClickable&&(it.text?.toString()==label||it.contentDescription?.toString()==label)};if(node!=null)break;SystemClock.sleep(60)}
   check(node!=null){"Control not visible after transition: $label"}
   check(node!!.performAction(AccessibilityNodeInfo.ACTION_CLICK));instrumentation.waitForIdleSync();SystemClock.sleep(350)
  }
  try{
   val layout=CloudActivity::class.java.getDeclaredField("layout").apply{isAccessible=true}.get(activity) as WorkspaceLayout
   val go=CloudActivity::class.java.getDeclaredMethod("goToPage",String::class.java).apply{isAccessible=true}
   var enabled=false;var before=0f
   instrumentation.runOnMainSync{enabled=ValueAnimator.areAnimatorsEnabled();before=layout.nav.getChildAt(0).translationX;go.invoke(activity,"ajustes")}
   var contentMoved=false;var indicatorMoved=false;val positions=mutableListOf<Float>();val frames=org.json.JSONArray()
   repeat(16){
    SystemClock.sleep(30)
    instrumentation.runOnMainSync{
     if(layout.scroll.alpha<.99f||kotlin.math.abs(layout.scroll.translationX)>.1f)contentMoved=true
     val x=layout.nav.getChildAt(0).translationX
     positions.add(x);frames.put(org.json.JSONObject().put("x",x).put("alpha",layout.scroll.alpha).put("content_x",layout.scroll.translationX))
    }
   }
   instrumentation.runOnMainSync{
    check(layout.scroll.alpha==1f&&layout.scroll.translationX==0f){"Transition did not settle"}
    check(layout.nav.getChildAt(0).translationX>before+50f){"Selection did not move"}
   }
   val end=positions.last();indicatorMoved=positions.any{it>before+1f&&it<end-1f}
   java.io.File(activity.cacheDir,"v074-motion-frames.json").writeText(org.json.JSONObject().put("before",before).put("end",end).put("frames",frames).toString())
   if(enabled){check(contentMoved){"No visible content transition"};check(indicatorMoved){"No intermediate navigation positions"}}
   else check(!contentMoved){"Reduced motion was ignored"}
   capture("v074-ajustes")
   var chosen=-1
   instrumentation.runOnMainSync{layout.ui.choose("Selecciona un aula",listOf("Aula Norte","Aula Sur"),0){chosen=it}}
   capture("v074-selector-aulas-fixture")
   check(nodes().none{it.className=="android.widget.CheckedTextView"||it.className=="android.widget.RadioButton"})
   click("Cancelar");check(chosen==-1)
   instrumentation.runOnMainSync{layout.ui.choose("Selecciona un aula",listOf("Aula Norte","Aula Sur"),0){chosen=it}}
   click("Aula Sur");check(chosen==1)
   instrumentation.runOnMainSync{layout.ui.choose("Selecciona un aula",listOf("Aula Norte","Aula Sur"),1){chosen=it}}
   capture("v074-selector-confirmado-fixture");click("Cancelar")
   val evidence="{\"system_animations_enabled\":$enabled,\"content_intermediate_frames\":$contentMoved,\"indicator_intermediate_positions\":$indicatorMoved,\"selector_cancel_and_selection\":true,\"cloud_calls\":false}"
   java.io.File(activity.cacheDir,if(enabled)"v074-motion.json" else "v074-reduced-motion.json").writeText(evidence)
  }finally{instrumentation.runOnMainSync{activity.finish()}}
 }
}
