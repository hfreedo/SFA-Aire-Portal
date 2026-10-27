package org.sfa.aire

import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.data.notifications.LocalNotificationPolicy
import org.sfa.aire.data.session.LanSession
import org.sfa.aire.data.session.LanConnection

class LocalNotificationPolicyTest {
    private val receiver="11111111-1111-4111-8111-111111111111"
    private val binding="22222222-2222-4222-8222-222222222222"
    private val delivery="33333333-3333-4333-8333-333333333333"
    private val session=LanSession(LanConnection("http://127.0.0.1:8766","fixture-only"),1,binding,receiver)
    private val data=mapOf("channel" to "local","local_contract" to "2","receiver_id" to receiver,"notification_binding" to binding,"delivery_id" to delivery)
    @Test fun verifiedLocalContextAcceptsItsOwnPayload(){assertTrue(LocalNotificationPolicy.accepts(data,session))}
    @Test fun lateOtherReceiverOrBindingNeverMatches(){
        assertFalse(LocalNotificationPolicy.accepts(data+("receiver_id" to delivery),session))
        assertFalse(LocalNotificationPolicy.accepts(data+("notification_binding" to delivery),session))
    }
    @Test fun legacyOrUnverifiedPayloadCannotInventIdentity(){
        assertFalse(LocalNotificationPolicy.accepts(data-"notification_binding",session))
        assertFalse(LocalNotificationPolicy.accepts(data,session.copy(receiverId=null)))
        assertFalse(LocalNotificationPolicy.accepts(data+("local_contract" to "1"),session))
    }
    @Test fun rejectsMalformedDeliveryAndMissingReceiver(){
        assertFalse(LocalNotificationPolicy.accepts(data+("delivery_id" to "1-1-1-1-1"),session))
        assertFalse(LocalNotificationPolicy.accepts(data-"receiver_id",session))
    }
}
