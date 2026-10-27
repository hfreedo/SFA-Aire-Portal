package org.sfa.aire.domain
import java.time.Instant

data class CarePermissions(val canTake:Boolean,val canContext:Boolean,val directing:Boolean,val closed:Boolean)
object CarePolicy {
    fun permissions(actor:String,current:String,coordinator:String?,teacher:String?,deputy:String?,status:String):CarePermissions {
        val known=actor.isNotBlank()&&actor!="null"&&status in listOf("pendiente","en_atencion","resuelto")
        val closed=status=="resuelto"
        val directing=known&&current==actor
        return CarePermissions(known&&!closed&&actor in listOf(coordinator,deputy)&&!directing,known&&!closed&&(actor==teacher||directing),directing,closed)
    }
    fun expiresAt(value:String):Long?=try{Instant.parse(value).toEpochMilli()}catch(_:Exception){null}
    fun responses(actor:String,recipient:String,status:String,expires:Long?,now:Long):List<String> {
        if(actor.isBlank()||actor=="null"||actor!=recipient||expires==null||expires<=now||status !in listOf("emitida","confirmada","aclaracion","impedimento","parcial"))return emptyList()
        return listOf("confirmada","aclaracion","impedimento")+if(status in listOf("confirmada","parcial"))listOf("parcial","realizada")else emptyList()
    }
}
