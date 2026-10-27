package org.sfa.aire.data.notifications

import java.util.UUID

data class PendingReceipt(val route:String,val delivery:String,val action:String,val generation:Long?,val receiverId:String?=null,val binding:String?=null)
/** Acuses de contratos anteriores se decodifican para retirarlos, nunca se les asigna identidad nueva. */
object ReceiptCodec {
    fun encode(route:String,delivery:String,action:String,generation:Long?=null,receiverId:String?=null,binding:String?=null):String? {
        if(!valid(delivery,action)||route !in listOf("cloud","local")||generation==null||generation<0)return null
        if(route=="cloud")return "cloud2@$generation|$delivery|$action"
        if(!uuid(receiverId)||!uuid(binding))return null
        return "local3@$generation|$receiverId|$binding|$delivery|$action"
    }
    fun decode(value:String):PendingReceipt? {
        if(value.length>256)return null
        val parts=value.split('|')
        if(parts.size==5&&parts[0].startsWith("local3@")){
            val gen=parts[0].substringAfter('@').toLongOrNull()?:return null
            return if(gen>=0&&uuid(parts[1])&&uuid(parts[2])&&valid(parts[3],parts[4]))PendingReceipt("local",parts[3],parts[4],gen,parts[1],parts[2])else null
        }
        if(parts.size==2)return if(valid(parts[0],parts[1]))PendingReceipt("local",parts[0],parts[1],null)else null
        if(parts.size!=3||!valid(parts[1],parts[2]))return null
        if(parts[0]=="local")return PendingReceipt("local",parts[1],parts[2],null)
        val route=when{parts[0].startsWith("cloud2@") -> "cloud";parts[0].startsWith("local2@") -> "local";else -> return null}
        val gen=parts[0].substringAfter('@').toLongOrNull()?:return null
        return if(gen>=0)PendingReceipt(route,parts[1],parts[2],gen)else null
    }
    private fun valid(delivery:String,action:String)=action in listOf("recibido","abierto")&&uuid(delivery)
    private fun uuid(value:String?):Boolean=try{value!=null&&UUID.fromString(value).toString().equals(value,ignoreCase=true)}catch(_:Exception){false}
}
