package org.sfa.aire.ui.screens
import android.graphics.Color
import android.view.Gravity
import android.widget.LinearLayout
import android.widget.HorizontalScrollView
import org.json.JSONObject
import org.sfa.aire.ui.AireUi
import org.sfa.aire.domain.NoticePresentation
import org.sfa.aire.domain.NoticeInbox
import org.sfa.aire.domain.InboxFilter

/** Una bandeja personal; atención global, nota y archivo son acciones independientes. */
class IncidentsScreen(private val ui:AireUi,private val close:(JSONObject)->Unit,private val allowed:Boolean,private val share:(JSONObject)->Unit,private val comment:((JSONObject)->Unit)?=null){
 private fun date(raw:String):String=try{java.text.DateFormat.getDateTimeInstance(java.text.DateFormat.SHORT,java.text.DateFormat.SHORT,ui.locale).format(java.util.Date(java.time.Instant.parse(raw).toEpochMilli()))}catch(_:Exception){"Sin fecha verificable"}
 fun render(data:JSONObject,incidents:List<JSONObject>,focusedId:String?=null,
  filter:InboxFilter=InboxFilter.PENDING,archived:Set<String> = emptySet(),
  onFilter:((InboxFilter)->Unit)?=null,onArchive:((JSONObject,Boolean)->Unit)?=null){with(ui){
  val wideTabs=activity.resources.configuration.fontScale>1.2f||activity.resources.configuration.screenWidthDp<340
  val filters=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL}
  if(wideTabs)root.addView(HorizontalScrollView(activity).apply{
   isHorizontalScrollBarEnabled=false;contentDescription="Categorías de avisos. Desliza horizontalmente para ver todas."
   addView(filters,LinearLayout.LayoutParams(-2,-2))
  },LinearLayout.LayoutParams(-1,-2)) else root.addView(filters)
  for(option in InboxFilter.values()){
   val count=incidents.count{NoticeInbox.category(it.optString("id"),it.optString("status"),archived)==option}
   secondary(filters,"${option.title}\n$count"){onFilter?.invoke(option)}.apply{
    textSize=14f;minimumWidth=0;minimumHeight=dp(60);gravity=Gravity.CENTER;isSelected=filter==option
    layoutParams=(if(wideTabs)LinearLayout.LayoutParams(-2,-2) else LinearLayout.LayoutParams(0,-2,1f)).apply{marginEnd=dp(if(option==InboxFilter.ARCHIVED)0 else 6);bottomMargin=dp(12)}
    if(wideTabs){minimumWidth=dp(124);setHorizontallyScrolling(true)}
    surface(this,if(filter==option)sage else Color.WHITE,if(filter==option)green else muted)
    isEnabled=true;contentDescription="${option.title}, $count avisos"+(if(filter==option)", seleccionado" else "")
   }
  }
  if(wideTabs)filters.post{filters.getChildAt(filter.ordinal)?.let{selected->selected.requestRectangleOnScreen(android.graphics.Rect(0,0,selected.width,selected.height),true)}}
  if(filter==InboxFilter.ARCHIVED)text(root,"Archivo personal de este teléfono. Archivar no marca el aviso como atendido.",14f)
  val visible=incidents.filter{NoticeInbox.category(it.optString("id"),it.optString("status"),archived)==filter}
    .sortedWith(compareBy<JSONObject>{if(it.optString("id")==focusedId)0 else 1}.thenByDescending{it.optString("opened_at")})
  if(visible.isEmpty()){
   val box=card();text(box,when(filter){InboxFilter.PENDING->"Sin avisos pendientes";InboxFilter.ATTENDED->"Sin avisos atendidos";InboxFilter.ARCHIVED->"Archivo vacío"},18f,true)
   text(box,if(filter==InboxFilter.ARCHIVED)"Los avisos que archives en este teléfono aparecerán aquí." else "Los avisos recientes de esta aula se organizan en las pestañas superiores.",14f)
  }
  for(item in visible){
   val closed=item.optString("status")=="resuelto";val simulated=item.optString("source")=="simulacion";val alert=item.optString("severity")=="alerta"
   val box=card();val tags=LinearLayout(activity);box.addView(tags)
   badge(tags,if(simulated)"SIMULACIÓN" else "ARDUINO",if(simulated)simulationSurface else sage,if(simulated)simulationInk else green)
   badge(tags,if(closed)"ATENDIDO" else "PENDIENTE",if(closed)neutralSurface else if(alert)alertSurface else warningSurface,if(closed)muted else if(alert)alertInk else warningInk)
   text(box,NoticePresentation.title(item.optString("source"),item.optString("severity"),closed),18f,true)
   text(box,date(item.optString("opened_at")),14f)
   val evidence=item.optJSONObject("trigger_observation")
   fun number(name:String)=(evidence?.opt(name) as? Number)?.toDouble()
   val dht=evidence?.opt("dht_ok")==true
   val temperature=NoticePresentation.measurement(if(dht)number("temperature") else null,-40.0,125.0,"°C",1)
   val humidity=NoticePresentation.measurement(if(dht)number("humidity") else null,0.0,100.0,"%")
   val mq=NoticePresentation.measurement(number("mq_raw"),0.0,1023.0,"ADC")
   text(box,if(evidence==null)"Sin lectura asociada conservada" else "$temperature · MQ135 $mq",14f,true)
   disclosure(box,"Detalles y acciones","notice-"+item.optString("id")){body->
    if(evidence==null)text(body,"Este aviso no conserva una lectura asociada. Consulta Mi aula para ver las mediciones actuales.",14f)
    else{
     space(body,8);text(body,if(simulated)"Datos simulados del aviso" else "Lectura asociada al aviso",16f,true)
     text(body,"Medición · "+date(item.optString("trigger_sample_at")),14f)
     meta(body,"Temperatura",temperature);meta(body,"Humedad",humidity);meta(body,"MQ135",mq)
     text(body,"Valores del aviso; no indican el estado actual. MQ135 es una señal relativa.",14f)
    }
    val note=item.optString("note").removePrefix("AVISO ATENDIDO · No confirma normalización del ambiente.").trim()
    if(note.isNotBlank())text(body,note,15f)
    if(closed)text(body,"Consulta Mi aula para conocer la medición actual.",14f)
    val deliveries=data.getJSONArray("deliveries")
    val own=(0 until deliveries.length()).map{deliveries.getJSONObject(it)}.filter{it.optString("incident_id")==item.optString("id")}
    val failed=own.count{it.optString("status") in listOf("error","vencido")}
    val omitted=item.optInt("push_omitted_operational")+item.optInt("push_omitted_laboratory")
    if(failed>0)text(body,"Hay entregas sin recepción confirmada. Revisa los detalles.",14f,true)
    if(omitted>0)text(body,"Límite preventivo alcanzado: hay entregas sin programar.",14f,true)
    if(!closed){
     val capabilities=item.optJSONObject("capabilities");val canClose=capabilities?.opt("can_resolve")==true
     actionButton(body,"Marcar atendido",allowed&&canClose){close(item)}
     if(comment!=null)rowAction(body,"Atender con nota","note"){comment.invoke(item)}.apply{isEnabled=isEnabled&&allowed&&canClose;alpha=1f}
     if(!canClose)text(body,capabilities?.optString("resolve_reason")?.takeIf{it.isNotBlank()&&it!="null"}?:"Actualiza el estado para verificar permisos de atención.",14f)
    }
    rowAction(body,"Compartir aviso","share"){share(item)}.apply{isEnabled=true;alpha=1f}
    if(onArchive!=null)rowAction(body,if(item.optString("id") in archived)"Restaurar en la bandeja" else "Archivar en este teléfono","archive"){onArchive.invoke(item,item.optString("id") !in archived)}.apply{isEnabled=true;alpha=1f}
    disclosure(body,"Detalles de entrega","delivery-"+item.optString("id")){details->
     text(details,if(own.isEmpty())"Sin entregas registradas" else "Recibidas por la app: "+own.count{!it.isNull("received_at")}+" / "+own.size+" entregas visibles",14f)
     if(failed>0)text(details,"$failed entregas sin recepción confirmada por error o vencimiento.",14f)
     if(omitted>0)text(details,"$omitted entregas sin programar por el límite diario.",14f)
     text(details,"Recibir, archivar o atender un aviso no confirma la normalización del ambiente.",14f)
    }
   }
  }
 }}
}
