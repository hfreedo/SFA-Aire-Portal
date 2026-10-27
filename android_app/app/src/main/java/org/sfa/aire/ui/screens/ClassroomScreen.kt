package org.sfa.aire.ui.screens

import android.app.AlertDialog
import android.graphics.Color
import android.view.Gravity
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ScrollView
import org.json.JSONObject
import org.sfa.aire.ui.AireUi
import org.sfa.aire.ui.AireIcon
import org.sfa.aire.domain.ObservationState
import java.util.Locale

/** Lecturas de solo consulta. La identidad y la antigüedad no dependen de su color. */
class ClassroomScreen(private val ui:AireUi){
 private fun number(sample:JSONObject,key:String,decimals:Int=1):String {
  val value=sample.optDouble(key,Double.NaN)
  return if(!value.isFinite())"—" else String.format(Locale.getDefault(),"%.$decimals"+"f",value)
 }
 private fun sensorTile(parent:LinearLayout,title:String,value:String,unit:String,kind:String,color:Int,detail:String){with(ui){
  val tile=column().apply{background=shape(color);setPadding(dp(17),dp(18),dp(13),dp(18))}
  parent.addView(tile,if(parent.orientation==LinearLayout.HORIZONTAL)LinearLayout.LayoutParams(0,-1,1f).apply{if(kind=="temperature")marginEnd=dp(12)} else LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(12)})
  tile.addView(ImageView(activity).apply{setImageDrawable(AireIcon(activity,kind,green,32));importantForAccessibility=android.view.View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(32),dp(32)).apply{bottomMargin=dp(12)})
  text(tile,title,16f,true);text(tile,value,34f,true);text(tile,unit,15f,true);text(tile,detail,14f)
 }}
 private fun information(){with(ui){
  val content=column().apply{setPadding(dp(22),dp(12),dp(22),dp(20))}
  text(content,"Temperatura · DHT",20f,true)
  text(content,"Muestra la temperatura del sensor DHT instalado, en grados Celsius (°C). La humedad se presenta por separado, en porcentaje.")
  text(content,"Si el DHT no entrega una lectura válida, se muestra —. Los umbrales de aviso se configuran en el portal de la PC.",14f)
  text(content,"MQ135 · Señal relativa",20f,true)
  text(content,"El valor ADC es la lectura de la entrada analógica del Arduino UNO, de 0 a 1023. La relación × referencia compara esa señal con la referencia configurada.")
  text(content,"Una relación 1,50 × significa una señal un 50 % mayor que esa referencia. No equivale a una concentración de contaminantes ni identifica un gas.",14f)
  text(content,"No es CO₂, AQI ni ppm",17f,true)
  text(content,"Sin un modelo y validación específicos, esta maqueta no convierte el MQ135 a esas unidades. Si falta referencia o acondicionamiento, la app lo señala.",14f)
  text(content,"Lecturas reales y simuladas",20f,true)
  text(content,"SIMULACIÓN identifica un ensayo. Una lectura vencida se conserva como histórica y no describe el ambiente actual. La atención de un aviso no modifica la medición.",14f)
  AlertDialog.Builder(activity).setTitle("Información de sensores").setView(ScrollView(activity).apply{addView(content)}).setPositiveButton("Entendido",null).show()
 }}
 fun render(data:JSONObject,roomId:String,incidents:List<JSONObject>,freshnessUpdates:MutableList<()->Unit>,onIncidents:()->Unit,onRefresh:()->Unit){with(ui){
  val pending=incidents.count{it.optString("status")!="resuelto"}
  val snapshots=data.getJSONArray("snapshots");var count=0
  for(n in 0 until snapshots.length()){
   val s=snapshots.getJSONObject(n);if(s.optString("classroom_id")!=roomId)continue;count++
   val observation=ObservationState.from(s.optString("sample_at"),s.optString("state"));val sample=s.getJSONObject("observation")
   val header=card()
   val source=text(header,if(s.optString("source")=="simulacion")"SIMULACIÓN" else "ARDUINO · LECTURA REAL",14f,true)
   source.setTextColor(if(s.optString("source")=="simulacion")Color.rgb(123,76,34) else green)
   val stateText=text(header,observation.label,23f,true)
   val historical=text(header,if(observation.fresh)"El ambiente de tu aula, a la vista." else "Valores históricos · Sin lectura actual",14f)
   val ageText=text(header,observation.ageLabel,14f)
   fun update(){
    val current=ObservationState.from(s.optString("sample_at"),s.optString("state"));stateText.text=current.label;ageText.text=current.ageLabel
    historical.text="Valores históricos · Sin lectura actual";historical.visibility=if(current.fresh)android.view.View.GONE else android.view.View.VISIBLE
    header.background=shape(if(!current.fresh)Color.rgb(255,245,224) else if(current.state=="alerta")Color.rgb(255,238,226) else Color.WHITE)
   }
   update();freshnessUpdates.add{update()}
   if(pending>0)secondary(header,"Revisar avisos ($pending)",onIncidents).apply{isEnabled=true;alpha=1f}
   val metrics=LinearLayout(activity).apply{orientation=if(activity.resources.configuration.fontScale>1.2f||activity.resources.configuration.screenWidthDp<340)LinearLayout.VERTICAL else LinearLayout.HORIZONTAL}
   root.addView(metrics,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(14)})
   val dht=sample.optBoolean("dht_ok")
   sensorTile(metrics,"Temperatura",if(dht)number(sample,"temperature") else "—","°C","temperature",sage,if(dht)"Sensor DHT" else "DHT sin lectura")
   sensorTile(metrics,"MQ135",number(sample,"mq_raw",0),"ADC","air",sageStrong,if(sample.isNull("ratio"))"Sin referencia" else number(sample,"ratio",2)+" × referencia")
   val humidity=card();val row=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL};humidity.addView(row,LinearLayout.LayoutParams(-1,-2))
   row.addView(ImageView(activity).apply{setImageDrawable(AireIcon(activity,"humidity",green));importantForAccessibility=android.view.View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(28),dp(28)).apply{marginEnd=dp(12)})
   val caption=column();row.addView(caption,LinearLayout.LayoutParams(0,-2,1f));text(caption,"Humedad",16f,true);text(caption,"Lectura del DHT",14f)
   text(row,(if(dht)number(sample,"humidity",0) else "—")+" %",23f,true)
  }
  if(count==0){val box=card();text(box,"Esperando mediciones",22f,true);text(box,"La PC del aula todavía no sincronizó una lectura. Revisa la conexión Arduino en el portal.")}
  if(pending==0){val notice=card();text(notice,"Sin avisos pendientes",16f,true)}
  val info=secondary(root,"Información de sensores"){information()};info.isEnabled=true;info.alpha=1f;info.setCompoundDrawablesWithIntrinsicBounds(AireIcon(activity,"info",green,20),null,null,null)
  secondary(root,"Actualizar aula",onRefresh)
 }}
}
