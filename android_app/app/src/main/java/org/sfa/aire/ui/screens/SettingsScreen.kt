package org.sfa.aire.ui.screens
import android.graphics.Color
import android.widget.Switch
import org.sfa.aire.ui.AireUi

data class SettingsState(val demo:Boolean,val email:String,val permitted:Boolean,val simulations:Boolean,val overflow:Boolean,val registered:Boolean=false,val room:String="Aula seleccionada")
class SettingsScreen(private val ui:AireUi){
 fun render(state:SettingsState,onRegister:(Boolean)->Unit,onPermission:()->Unit,onRefresh:()->Unit,onLocal:()->Unit,onLogout:()->Unit,onExitDemo:()->Unit){with(ui){
  text(root,"Ajustes",22f,true)
  val box=card();text(box,"Notificaciones",18f,true)
  badge(box,when{state.demo->"EJEMPLO · SIN REGISTRO REAL";state.registered&&state.permitted->"AVISOS ACTIVOS";!state.permitted->"PERMISO ANDROID PENDIENTE";else->"REGISTRO PENDIENTE"},if(state.registered&&state.permitted)sage else Color.rgb(255,244,220))
  text(box,if(state.demo)"Aula de ejemplo" else state.room,16f,true)
  if(!state.demo)text(box,when{state.registered&&state.permitted->"Este teléfono tiene permiso y registro confirmado para el aula.";state.registered->"El registro está confirmado. Habilita el permiso de Android para recibir avisos.";else->"Registro pendiente para esta sesión y aula. Activa los avisos para completar la configuración."},14f)
  val simulations=Switch(activity).apply{text="Incluir avisos de simulación";isChecked=state.simulations;textSize=16f;setTextColor(ink);isEnabled=!state.demo;minimumHeight=dp(48);setPadding(0,dp(7),0,dp(7));styleSwitch(this)};box.addView(simulations)
  val explanation=text(box,"Las pruebas se identifican como SIMULACIÓN.",14f)
  val registration=if(state.registered)secondary(box,"Actualizar registro"){onRegister(simulations.isChecked)} else button(box,"Activar avisos en este teléfono"){onRegister(simulations.isChecked)}
  simulations.setOnCheckedChangeListener{_,checked->
    val changed=checked!=state.simulations
    explanation.text=if(changed)"Cambios pendientes: pulsa Guardar preferencia." else "Las pruebas se identifican como SIMULACIÓN."
    registration.text=if(changed)"Guardar preferencia" else if(state.registered)"Actualizar registro" else "Activar avisos en este teléfono"
    surface(registration,if(changed||!state.registered)green else sage,if(changed||!state.registered)Color.WHITE else green)
  }
  if(!state.permitted&&!state.demo)button(box,"Revisar permiso de Android",onPermission)
  disclosure(box,"Detalles del registro","notification-details") {body->
    meta(body,"Permiso Android",if(state.demo)"Ejemplo" else if(state.permitted)"Habilitado" else "Desactivado")
    meta(body,"Registro del aula",if(state.demo)"Sin conexión real" else if(state.registered)"Confirmado" else "Pendiente")
    if(state.permitted&&!state.demo)secondary(body,"Permisos en Android",onPermission)
  }
  if(state.demo)text(box,"Vista de ejemplo. No registra el teléfono ni envía mensajes.",14f)
  if(state.overflow)text(root,"Algunos avisos pueden carecer de confirmación de recepción: la cola local de acuses alcanzó su capacidad. Consulta al administrador.",14f)
  val account=card();text(account,"Cuenta",18f,true);text(account,if(state.demo)"Sin sesión real · Demostración" else state.email,16f)
  if(!state.demo)secondary(account,"Actualizar estado",onRefresh)
  disclosure(account,"Más opciones","account-options") {body->
    secondary(body,"Conexión local avanzada",onLocal)
    if(!state.demo)secondary(body,"Cerrar sesión y desvincular teléfono",onLogout)
  }
  if(state.demo)secondary(root,"Salir de la demostración",onExitDemo).apply{isEnabled=true;alpha=1f}
  text(root,"SFA Aire · "+org.sfa.aire.BuildConfig.VERSION_NAME,14f)
 }}
}
