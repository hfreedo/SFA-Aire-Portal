package org.sfa.aire.data.notifications

import org.sfa.aire.data.session.LanConnectionRepository
import org.sfa.aire.data.session.LanSession

/** La identidad procede del estado autenticado; el payload FCM nunca cambia la conexión. */
object LocalNotificationPolicy {
    fun accepts(data:Map<String,String>,session:LanSession):Boolean =
        data["channel"]=="local"&&data["local_contract"]=="2"&&session.receiverId!=null&&
        data["receiver_id"]==session.receiverId&&data["notification_binding"]==session.binding&&
        LanConnectionRepository.validId(data["delivery_id"])
}
