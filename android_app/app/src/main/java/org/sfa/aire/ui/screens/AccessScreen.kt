package org.sfa.aire.ui.screens
import android.graphics.Color
import android.text.InputType
import android.content.Intent
import android.net.Uri
import org.sfa.aire.ui.AireUi

class AccessScreen(private val ui:AireUi){
    fun render(configured:Boolean,rememberedEmail:String,onLogin:(String,String)->Unit,onDemo:()->Unit,onLocal:()->Unit){with(ui){
        val welcome=card(color=sage);text(welcome,"Tu aula,\na la vista.",32f,true);text(welcome,"Temperatura, señal del aire y avisos en un mismo lugar.",16f)
        val form=card();text(form,"Ingresar al monitoreo",21f,true);text(form,"Usa la cuenta asignada por el administrador.",14f)
        text(form,if(configured)"Acceso institucional configurado" else "Esta instalación necesita configuración del administrador.",12f)
        val email=input(form,"Correo electrónico",rememberedEmail).apply{inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS}
        val password=input(form,"Contraseña","",true)
        button(form,"Ingresar"){
            if(email.text.toString().isBlank()){email.error="Escriba el correo"}
            else if(password.text.toString().isEmpty()){password.error="Escriba la contraseña"}
            else {val secret=password.text.toString();password.setText("");onLogin(email.text.toString(),secret)}
        }.isEnabled=configured
        secondary(root,"Tengo una invitación"){
            root.context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse("https://sfa-aire-aulas.web.app/invitacion")))
        }
        text(root,"Abre tu enlace de invitación en el navegador para activar la cuenta. Luego ingresa aquí con tu correo y contraseña.",14f)
        secondary(root,"Explorar demostración",onDemo)
        secondary(root,"Conexión local avanzada",onLocal)
        text(root,"Señal MQ135 relativa, temperatura y humedad.",12f)
    }}
}
