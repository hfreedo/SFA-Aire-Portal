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
  return if(!value.isFinite())"—" else String.format(ui.locale,"%.$decimals"+"f",value)
 }
 private data class SensorViews(val box:LinearLayout,val value:android.widget.TextView,val detail:android.widget.TextView)
 private fun sensorTile(parent:LinearLayout,title:String,kind:String):SensorViews=with(ui){
  val tile=column().apply{background=shape(Color.WHITE,sageStrong);setPadding(dp(12),dp(12),dp(12),dp(12))}
  parent.addView(tile,if(parent.orientation==LinearLayout.HORIZONTAL)LinearLayout.LayoutParams(0,-1,1f).apply{if(kind=="temperature")marginEnd=dp(12)} else LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(10)})
  val label=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL};tile.addView(label)
  label.addView(ImageView(activity).apply{setImageDrawable(AireIcon(activity,kind,sensorColor(kind),21));background=shape(sensorSurface(kind),radius=6);setPadding(dp(3),dp(3),dp(3),dp(3));importantForAccessibility=android.view.View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(24),dp(24)).apply{marginEnd=dp(8)})
  text(label,title,14f)
  space(tile,6)
  SensorViews(tile,text(tile,"—",28f,true),text(tile,"",14f))
 }
 private fun value(view:android.widget.TextView,number:String,unit:String){
  val formatted=android.text.SpannableString("$number $unit")
  formatted.setSpan(android.text.style.RelativeSizeSpan(.55f),number.length+1,formatted.length,0)
  view.text=formatted
 }
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
  val dialog=dialogBuilder("Información de sensores").setView(ScrollView(activity).apply{addView(content)}).setPositiveButton("Entendido",null).show()
  styleDialog(dialog)
 }}
 fun render(data:JSONObject,roomId:String,incidents:List<JSONObject>,freshnessUpdates:MutableList<()->Unit>,onIncidents:()->Unit,onRefresh:()->Unit,dataUpdates:MutableList<(JSONObject)->Unit> = mutableListOf()){with(ui){
  val pending=incidents.count{it.optString("status")!="resuelto"}
  val snapshots=data.getJSONArray("snapshots");var count=0
  for(n in 0 until snapshots.length()){
   val initial=snapshots.getJSONObject(n);if(initial.optString("classroom_id")!=roomId)continue;count++
   var snapshot=initial
   val header=card()
   val statusRow=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL};header.addView(statusRow)
   val content=column();statusRow.addView(content,LinearLayout.LayoutParams(0,-2,1f))
   val tags=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL};content.addView(tags)
   val source=badge(tags,"")
   val stale=badge(tags,"LECTURA VENCIDA",warningSurface,warningInk)
   val stateText=text(content,"",18f,true)
   val historical=text(content,"Última lectura · No describe el ambiente actual",14f)
   val ageText=text(content,"",14f)
   val exact=text(content,"",14f).apply{visibility=android.view.View.GONE}
   ageText.minimumHeight=dp(48);ageText.gravity=Gravity.CENTER_VERTICAL;ageText.isClickable=true;ageText.isFocusable=true
   ageText.setCompoundDrawablesWithIntrinsicBounds(null,null,AireIcon(activity,"info",green,18),null)
   ageText.compoundDrawablePadding=dp(8)
   ageText.setOnClickListener{exact.visibility=if(exact.visibility==android.view.View.VISIBLE)android.view.View.GONE else android.view.View.VISIBLE}
   if(pending>0)tertiary(statusRow,if(pending==1)"Ver aviso" else "Ver avisos",onIncidents).apply{
       surface(this,Color.WHITE,green);contentDescription="$pending avisos pendientes. Revisar avisos";isEnabled=true;alpha=1f;gravity=Gravity.CENTER;setPadding(dp(4),dp(8),dp(4),dp(8))
       layoutParams=LinearLayout.LayoutParams(dp(88),-2).apply{marginStart=dp(8)}
   }
   val metricHeading=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL}
   root.addView(metricHeading,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(8)})
   text(metricHeading,"Mediciones",18f,true).layoutParams=LinearLayout.LayoutParams(0,-2,1f)
   iconAction(metricHeading,"Información de sensores","info"){information()}
   val metrics=LinearLayout(activity).apply{orientation=if(activity.resources.configuration.fontScale>1.2f||activity.resources.configuration.screenWidthDp<340)LinearLayout.VERTICAL else LinearLayout.HORIZONTAL}
   root.addView(metrics,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(12)})
   val temperature=sensorTile(metrics,"Temperatura","temperature")
   val mq=sensorTile(metrics,"MQ135","air")
   val humidity=card().apply{setPadding(dp(12),dp(10),dp(12),dp(10))};val row=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL};humidity.addView(row,LinearLayout.LayoutParams(-1,-2))
   row.addView(ImageView(activity).apply{setImageDrawable(AireIcon(activity,"humidity",sensorColor("humidity"),22));importantForAccessibility=android.view.View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(24),dp(24)).apply{marginEnd=dp(10)})
   text(row,"Humedad",16f,true).layoutParams=LinearLayout.LayoutParams(0,-2,1f)
   val humidityValue=text(row,"—",21f,true)
   fun update(){
    val current=ObservationState.from(snapshot.optString("sample_at"),snapshot.optString("state"))
    val sample=snapshot.getJSONObject("observation");val dht=sample.optBoolean("dht_ok")
    val simulated=snapshot.optString("source")=="simulacion"
    source.text=if(simulated)"SIMULACIÓN" else "ARDUINO · REAL"
    source.background=shape(if(simulated)simulationSurface else sage,radius=6)
    source.setTextColor(if(simulated)simulationInk else green)
    stale.visibility=if(current.fresh)android.view.View.GONE else android.view.View.VISIBLE
    stateText.text=current.label
    historical.visibility=if(current.fresh)android.view.View.GONE else android.view.View.VISIBLE
    ageText.text=current.ageLabel
    exact.text=try{java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.MEDIUM,java.text.DateFormat.SHORT,locale).format(java.util.Date(java.time.Instant.parse(snapshot.getString("sample_at")).toEpochMilli()))}catch(_:Exception){"Fecha no verificable"}
    ageText.contentDescription=current.ageLabel+". Mostrar fecha exacta de la lectura."
    header.background=shape(Color.WHITE,outline)
    stateText.setTextColor(if(!current.fresh)muted else if(current.state=="alerta")alertInk else if(current.state=="aviso")warningInk else ink)
    temperature.box.background=shape(if(current.fresh)Color.WHITE else neutralSurface,sageStrong)
    mq.box.background=shape(if(current.fresh)Color.WHITE else neutralSurface,sageStrong)
    value(temperature.value,if(dht)number(sample,"temperature") else "—","°C")
    temperature.detail.text=if(!dht)"DHT sin lectura" else if(current.fresh)"Sensor DHT" else "Última lectura · DHT"
    value(mq.value,number(sample,"mq_raw",0),"ADC")
    mq.detail.text=(if(current.fresh)"" else "Última lectura · ")+(if(sample.isNull("ratio"))"Sin referencia" else number(sample,"ratio",2)+" × referencia")
    humidityValue.text=(if(dht)number(sample,"humidity",0) else "—")+" %"
    temperature.value.setTextColor(if(current.fresh)ink else muted);mq.value.setTextColor(if(current.fresh)ink else muted);humidityValue.setTextColor(if(current.fresh)ink else muted)
   }
   update();freshnessUpdates.add{update()}
   dataUpdates.add{newData->newData.optJSONArray("snapshots")?.optJSONObject(n)?.takeIf{it.optString("classroom_id")==roomId}?.let{snapshot=it;update()}}
  }
  if(count==0){val box=card();text(box,"Esperando mediciones",21f,true);text(box,"La PC del aula todavía no sincronizó una lectura. Revisa la conexión Arduino en el portal.")}
  if(pending==0){val notice=card();text(notice,"Sin avisos pendientes",16f,true)}
  if(count==0)tertiary(root,"Información de sensores"){information()}.apply{isEnabled=true;alpha=1f}
  rowAction(root,"Actualizar aula","refresh",onRefresh)

 }}
}
