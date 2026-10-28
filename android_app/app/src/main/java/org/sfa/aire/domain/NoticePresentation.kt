package org.sfa.aire.domain

import java.util.Locale

/** Copy común de bandeja y aviso; el color nunca sustituye el origen/severidad. */
object NoticePresentation {
    fun title(source:String,severity:String,closed:Boolean=false):String {
        if(closed)return "Aviso atendido"
        val alert=severity=="alerta"
        return if(source=="simulacion") {if(alert)"Alerta simulada" else "Aviso simulado"}
          else if(alert)"Alerta del aula" else "Aviso del aula"
    }
    fun measurement(value:Double?,min:Double,max:Double,unit:String,decimals:Int=0):String {
        if(value==null||!value.isFinite()||value<min||value>max)return "No disponible"
        return String.format(Locale.forLanguageTag("es-PY"),"%.${decimals}f",value)+" "+unit
    }
}
