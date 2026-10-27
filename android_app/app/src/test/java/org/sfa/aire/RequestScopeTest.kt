package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.application.RequestScope
class RequestScopeTest {
 @Test fun invalidationRejectsOldReadAndWriteCallbacks(){val gate=RequestScope();val ticket=gate.capture();assertTrue(gate.accepts(ticket));gate.invalidate();assertFalse(gate.accepts(ticket));assertTrue(gate.accepts(gate.capture()))}
 @Test fun returningToSameScreenDoesNotReacceptOldResult(){val gate=RequestScope();val old=gate.capture();gate.invalidate();gate.invalidate();assertFalse(gate.accepts(old))}
}
