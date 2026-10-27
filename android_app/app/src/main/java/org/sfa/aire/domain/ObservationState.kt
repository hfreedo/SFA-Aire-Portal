package org.sfa.aire.domain

import java.time.Instant

/** Caducidad de presentación; no sustituye la validación de la medición en servidor. */
data class ObservationState(val state:String,val ageSeconds:Long?,val fresh:Boolean){
    val label:String get()=labels[state]?:state
    val ageLabel:String get(){
        val seconds=ageSeconds?:return "Fecha de lectura no verificable"
        if(seconds < -5)return "Fecha de lectura adelantada · Revise el reloj"
        val age=when {
            seconds<60 -> "Hace unos segundos"
            seconds<3600 -> "Hace ${seconds/60} min"
            seconds<86400 -> "Hace ${seconds/3600} ${if(seconds/3600==1L)"hora" else "horas"}"
            else -> "Hace ${seconds/86400} ${if(seconds/86400==1L)"día" else "días"}"
        }
        return age
    }
    companion object {
        private val labels=mapOf("normal" to "Sin variación sostenida","alerta" to "Revisar ambiente","aviso" to "Variación sostenida","sin_datos" to "Sin datos recientes","fallo_sensor" to "Revisar sensores","calentando" to "Estabilizando sensor","sin_calibrar" to "Falta referencia")
        fun from(sampleAt:String,state:String,nowMillis:Long=System.currentTimeMillis()):ObservationState {
            val sample=try{Instant.parse(sampleAt).toEpochMilli()}catch(_:Exception){return ObservationState("sin_datos",null,false)}
            val elapsed=nowMillis.toDouble()-sample.toDouble()
            val fresh=elapsed>=-5000.0&&elapsed<=95000.0
            return ObservationState(if(fresh)state else "sin_datos",(elapsed/1000).toLong(),fresh)
        }
    }
}
