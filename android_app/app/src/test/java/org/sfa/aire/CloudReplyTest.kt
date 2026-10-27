package org.sfa.aire
import org.sfa.aire.data.network.*
import org.junit.Assert.*
import org.junit.Test

class CloudReplyTest {
    @Test fun preservesOverviewObject(){assertTrue(CloudReply.parse("{\"classrooms\":[]}").has("classrooms"))}
    @Test fun acceptsUuidAfterSavingInstruction(){assertEquals("11111111-1111-4111-8111-111111111111",CloudReply.parse("\"11111111-1111-4111-8111-111111111111\"").getString("result"))}
    @Test fun acceptsVoidAfterRegisteringPhone(){assertEquals(0,CloudReply.parse("null").length());assertEquals(0,CloudReply.parse("").length())}
}
