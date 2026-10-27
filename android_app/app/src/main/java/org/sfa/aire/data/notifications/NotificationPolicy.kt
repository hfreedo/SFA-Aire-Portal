package org.sfa.aire.data.notifications

import java.util.UUID

data class NotificationSession(val generation:Long,val binding:String)
/** Identificador opaco por sesión. No sustituye autorización RPC ni contiene el usuario. */
object NotificationPolicy {
    fun binding(installation:String,generation:Long):String=UUID.nameUUIDFromBytes(
        "sfa-aire:cloud-notifications:v2:$installation:$generation".toByteArray(Charsets.UTF_8)).toString()
    fun accepts(data:Map<String,String>,session:NotificationSession):Boolean =
        data["notification_contract"]=="2"&&data["installation_id"]==session.binding&&
        uuid(data["delivery_id"])&&uuid(data["classroom_id"])
    private fun uuid(value:String?):Boolean=try { value!=null&&UUID.fromString(value).toString()==value }catch(_:Exception){false}
}
