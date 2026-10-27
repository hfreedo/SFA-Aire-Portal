package org.sfa.aire.ui.screens
import android.graphics.Color
import android.view.View
import android.widget.Switch
import org.sfa.aire.ui.AireUi

data class SettingsState(val demo:Boolean,val email:String,val permitted:Boolean,val simulations:Boolean,val overflow:Boolean,val registered:Boolean=false,val room:String="Aula seleccionada",val registeredRoom:String?=null)
class SettingsScreen(private val ui:AireUi){
 fun render(state:SettingsState,onRegister:(Boolean)->Unit,onPermission:()->Unit,onRefresh:()->Unit,onLocal:()->Unit,onLogout:()->Unit,onExitDemo:()->Unit){with(ui){
  text(root,"Ajustes",22f,true);space(height=12)
  val box=card();text(box,"Avisos en este teléfono",18f,true);space(box,8)
  badge(box,when{state.demo->"EJEMPLO · SIN REGISTRO REAL";state.registered&&state.permitted->"AVISOS ACTIVOS";!state.permitted->"PERMISO ANDROID PENDIENTE";else->"REGISTRO PENDIENTE"},if(state.registered&&state.permitted)sage else Color.rgb(255,244,220))
  text(box,if(state.demo)"Aula de ejemplo" else state.room,16f,true)
  if(!state.demo&&!state.registered)text(box,if(state.registeredRoom!=null)"Este teléfono está registrado para ${state.registeredRoom}. Activa los avisos para el aula seleccionada." else "Registro pendiente para esta sesión y aula. Activa los avisos para completar la configuración.",14f)
  if(!state.demo&&!state.permitted)text(box,"Android tiene los avisos desactivados. Habilita el permiso para recibirlos.",14f)
  if(state.demo)text(box,"Vista de ejemplo. No registra el teléfono ni envía mensajes.",14f)
  divider(box)
  val simulations=Switch(activity).apply{text="Incluir simulaciones";isChecked=state.simulations;textSize=16f;setTextColor(ink);isEnabled=!state.demo&&state.permitted;minimumHeight=dp(48);setPadding(0,dp(8),0,dp(8));styleSwitch(this)};box.addView(simulations)
  val explanation=text(box,"Las pruebas llevan la etiqueta SIMULACIÓN.",14f)
  val registration=button(box,"Activar avisos en este teléfono"){onRegister(simulations.isChecked)}
  registration.visibility=if(!state.demo&&state.permitted&&!state.registered)View.VISIBLE else View.GONE
  simulations.setOnCheckedChangeListener{_,checked->
    val changed=checked!=state.simulations
    explanation.text=if(changed)"Preferencia sin guardar." else "Las pruebas llevan la etiqueta SIMULACIÓN."
    registration.text=if(changed)"Guardar preferencia" else "Activar avisos en este teléfono"
    registration.visibility=if(changed||!state.registered)View.VISIBLE else View.GONE
  }
  if(!state.permitted&&!state.demo)button(box,"Revisar permiso de Android",onPermission)
  disclosure(box,"Detalles del registro","notification-details") {body->
    space(body,8)
    meta(body,"Permiso Android",if(state.demo)"Ejemplo" else if(state.permitted)"Habilitado" else "Desactivado")
    meta(body,"Registro del aula",if(state.demo)"Sin conexión real" else if(state.registered)"Confirmado" else "Pendiente")
    if(state.permitted&&!state.demo){tertiary(body,"Actualizar registro"){onRegister(simulations.isChecked)};tertiary(body,"Permisos en Android",onPermission)}
  }
  if(state.overflow)text(root,"Hay confirmaciones de recepción pendientes porque la cola local está llena. Consulta al administrador.",14f)
  val account=card();text(account,"Cuenta",18f,true);space(account,8)
  text(account,if(state.demo)"Sin sesión real · Demostración" else state.email,16f)
  if(!state.demo)tertiary(account,"Actualizar estado",onRefresh)
  disclosure(account,"Más opciones","account-options") {body->
    tertiary(body,"Conexión local avanzada",onLocal)
    if(!state.demo)tertiary(body,"Cerrar sesión y desvincular teléfono",onLogout)
  }
  if(state.demo)tertiary(root,"Salir de la demostración",onExitDemo).apply{isEnabled=true;alpha=1f}
  text(root,"SFA Aire · "+org.sfa.aire.BuildConfig.VERSION_NAME,14f)
 }}
}
