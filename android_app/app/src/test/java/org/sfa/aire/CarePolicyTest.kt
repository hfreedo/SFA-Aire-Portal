package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.domain.CarePolicy
class CarePolicyTest {
 @Test fun unrelatedActorAndMissingIdentityCannotTakeOrAttend(){for(actor in listOf("", "null","outsider")){val p=CarePolicy.permissions(actor,"director","director","teacher","deputy","pendiente");assertFalse(p.canTake);assertFalse(p.canContext)}}
 @Test fun responsibleCanTakeAndTeacherCanContext(){assertTrue(CarePolicy.permissions("director","","director","teacher",null,"pendiente").canTake);assertTrue(CarePolicy.permissions("teacher","director","director","teacher",null,"pendiente").canContext)}
 @Test fun resolvedIncidentDoesNotOfferChanges(){val p=CarePolicy.permissions("director","director","director","teacher",null,"resuelto");assertFalse(p.canTake);assertFalse(p.canContext);assertTrue(p.closed)}
 @Test fun onlyRecipientWithValidInstructionCanRespond(){assertTrue(CarePolicy.responses("teacher","teacher","emitida",2000,1000).contains("confirmada"));for(expiry in listOf<Long?>(null,1000,0))assertTrue(CarePolicy.responses("teacher","teacher","emitida",expiry,1000).isEmpty());assertTrue(CarePolicy.responses("other","teacher","emitida",2000,1000).isEmpty());assertTrue(CarePolicy.responses("teacher","teacher","unknown",2000,1000).isEmpty())}
 @Test fun unknownIncidentStateDoesNotOfferCommands(){val p=CarePolicy.permissions("director","director","director","teacher",null,"unknown");assertFalse(p.directing);assertFalse(p.canTake);assertFalse(p.canContext)}
 @Test fun resultNeedsPriorComprehension(){assertFalse(CarePolicy.responses("teacher","teacher","emitida",2000,1000).contains("realizada"));assertTrue(CarePolicy.responses("teacher","teacher","confirmada",2000,1000).contains("realizada"));assertNull(CarePolicy.expiresAt("invalid"))}
}
