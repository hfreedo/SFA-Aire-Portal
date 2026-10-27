package org.sfa.aire.ui.screens
import android.graphics.Color
import android.widget.CheckBox
import org.sfa.aire.ui.AireUi

data class SettingsState(val demo:Boolean,val email:String,val permitted:Boolean,val simulations:Boolean,val overflow:Boolean,val registered:Boolean=false,val room:String="Aula seleccionada")
class SettingsScreen(private val ui:AireUi){
 fun render(state:SettingsState,onRegister:(Boolean)->Unit,onPermission:()->Unit,onRefresh:()->Unit,onLocal:()->Unit,onLogout:()->Unit,onExitDemo:()->Unit){with(ui){
  text(root,"Cuenta y notificaciones",24f,true)
  val account=card();text(account,if(state.demo)"Cuenta de ejemplo" else "Tu cuenta",18f,true);text(account,if(state.demo)"Sin sesión real" else state.email,16f)
  val box=card();text(box,"Avisos en este teléfono",20f,true);text(box,if(state.demo)"Aula de ejemplo" else state.room,14f,true)
  meta(box,"Permiso Android",if(state.demo)"Ejemplo" else if(state.permitted)"Habilitado" else "Desactivado")
  meta(box,"Registro del aula",if(state.demo)"Sin conexión real" else if(state.registered)"Confirmado" else "Pendiente")
  if(!state.demo)text(box,if(state.registered)"Registro de esta sesión confirmado para el aula." else "Registro pendiente para esta sesión y aula. Pulsa Registrar / actualizar notificaciones.",14f)
  val simulations=CheckBox(activity).apply{text="Recibir avisos de SIMULACIÓN";isChecked=state.simulations;textSize=15f;setTextColor(ink);buttonTintList=android.content.res.ColorStateList.valueOf(green);isEnabled=!state.demo;setPadding(0,dp(10),0,dp(6))};box.addView(simulations)
  button(box,"Registrar / actualizar notificaciones"){onRegister(simulations.isChecked)}
  secondary(box,"Revisar permiso de notificaciones",onPermission)
  if(state.demo)text(box,"Controles de ejemplo. No se registra el teléfono ni se envían mensajes.",14f)
  if(state.overflow)text(root,"La cola local de acuses alcanzó su capacidad. La recepción o apertura de algunos avisos puede no tener confirmación; consulta al administrador.",14f)
  if(!state.demo)secondary(root,"Actualizar estado",onRefresh)
  text(root,"Más opciones",16f,true)
  secondary(root,"Conexión local avanzada",onLocal)
  if(state.demo)secondary(root,"Salir de la demostración",onExitDemo).apply{isEnabled=true;alpha=1f}
  else secondary(root,"Cerrar sesión y desvincular este teléfono",onLogout)
  text(root,"SFA Aire · "+org.sfa.aire.BuildConfig.VERSION_NAME,14f)
 }}
}
