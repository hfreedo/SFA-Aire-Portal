package org.sfa.aire.ui

import android.app.AlertDialog
import android.graphics.Color
import android.text.InputFilter
import android.text.InputType
import android.view.Gravity
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/** Formularios conservan su contenido ante error; sus callbacks no conocen el transporte. */
class CareDialogs(private val ui:AireUi,private val canAct:()->Boolean,private val blocked:()->Boolean){
    private var dialog:AlertDialog?=null
    private var error:TextView?=null
    val isOpen:Boolean get()=dialog?.isShowing==true
    private fun attach(value:AlertDialog,message:TextView){
        dialog=value;error=message
        value.setOnDismissListener{if(dialog===value){dialog=null;error=null}}
    }
    fun note(title:String,hint:String,optional:Boolean=false,onSubmit:(String)->Unit){with(ui){
        if(blocked())return
        val form=column().apply{setPadding(dp(22),dp(8),dp(22),dp(12))}
        text(form,hint,14f);space(form,12)
        val note=EditText(activity).apply{this.hint=if(optional)"Nota opcional" else "Describa lo observado y el resultado…";minLines=3;maxLines=6;gravity=Gravity.TOP;inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE;filters=arrayOf(InputFilter.LengthFilter(500));styleField(this);setPadding(dp(12),dp(10),dp(12),dp(10));textSize=16f}
        form.addView(note,LinearLayout.LayoutParams(-1,-2))
        space(form,8)
        val message=text(form,if(optional)"Puede guardar sin escribir." else "Entre 3 y 500 caracteres. Si hay un error, su nota se conserva.",12f)
        val value=dialogBuilder(title).setView(form).setNegativeButton("Cancelar",null).setPositiveButton("Guardar",null).create()
        attach(value,message)
        value.setOnShowListener{
            styleDialog(value)
            value.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val text=note.text.toString().trim()
            if(text.length>500||(!optional&&text.length<3))note.error="Revise la longitud de la nota"
            else if(!canAct())message.text="Actualice el estado antes de guardar. La nota se conserva."
            else if(!blocked())onSubmit(text)
        }}
        value.show()
    }}
    fun instruction(id:String,onSubmit:(String,String,Int,String)->Unit){with(ui){
        if(blocked())return
        val form=column().apply{setPadding(dp(22),dp(8),dp(22),dp(12))}
        val action=input(form,"Acción concreta para el docente","")
        val reason=input(form,"Motivo de la decisión humana","")
        val minutes=input(form,"Vigencia en minutos (1 a 120)","30").apply{inputType=InputType.TYPE_CLASS_NUMBER}
        val message=text(form,"La indicación queda asociada al incidente y conserva su versión anterior.",12f)
        val value=dialogBuilder("Indicación vigente").setView(form).setNegativeButton("Cancelar",null).setPositiveButton("Emitir",null).create()
        attach(value,message)
        value.setOnShowListener{
            styleDialog(value)
            value.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
            val duration=minutes.text.toString().toIntOrNull()
            if(duration==null||duration !in 1..120||action.text.toString().trim().length !in 3..500||reason.text.toString().trim().length !in 3..500)message.text="Revise acción y motivo (3 a 500 caracteres) y vigencia (1 a 120 minutos)."
            else if(!canAct())message.text="Actualice el estado antes de emitir. El formulario se conserva."
            else if(!blocked())onSubmit(action.text.toString(),reason.text.toString(),duration,id)
        }}
        value.show()
    }}
    fun saving(value:Boolean){dialog?.let{it.setCancelable(!value);it.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=!value;it.getButton(AlertDialog.BUTTON_NEGATIVE).isEnabled=!value};if(value)error?.text="Guardando registro…"}
    fun failure(message:String){saving(false);error?.text="No se guardó: $message\nLa nota se conserva. Revise el motivo antes de reintentar."}
    fun dismiss(){dialog?.dismiss()}
}
