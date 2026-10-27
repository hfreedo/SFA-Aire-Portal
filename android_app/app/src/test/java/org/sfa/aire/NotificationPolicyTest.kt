package org.sfa.aire

import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.data.notifications.NotificationPolicy
import org.sfa.aire.data.notifications.NotificationSession

class NotificationPolicyTest {
    private val installation="11111111-1111-4111-8111-111111111111"
    private fun session(generation:Long)=NotificationSession(generation,NotificationPolicy.binding(installation,generation))
    private fun message(binding:String)=mapOf("notification_contract" to "2","installation_id" to binding,
        "delivery_id" to "22222222-2222-4222-8222-222222222222","classroom_id" to installation)
    @Test fun delayedMessageNeverBelongsToNewSessionInSameClassroom(){
        val a=session(1);val b=session(2)
        assertNotEquals(a.binding,b.binding)
        assertTrue(NotificationPolicy.accepts(message(a.binding),a))
        assertFalse(NotificationPolicy.accepts(message(a.binding),b))
    }
    @Test fun bindingSurvivesProcessRestartButNotLogoutOrAnotherDevice(){
        assertEquals(session(1),session(1))
        assertNotEquals(session(1).binding,NotificationPolicy.binding("another-device",1))
    }
    @Test fun legacyAndMalformedPayloadsAreRejected(){
        val a=session(1);val valid=message(a.binding)
        for(field in valid.keys)assertFalse(NotificationPolicy.accepts(valid-field,a))
        assertFalse(NotificationPolicy.accepts(valid+("notification_contract" to "1"),a))
        assertFalse(NotificationPolicy.accepts(valid+("delivery_id" to "1-1-1-1-1"),a))
        assertFalse(NotificationPolicy.accepts(valid+("classroom_id" to "../secret"),a))
    }
}
