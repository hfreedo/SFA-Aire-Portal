package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import org.sfa.aire.application.CareCommands
class CareCommandsTest {
 private fun item()=JSONObject().put("id","11111111-1111-4111-8111-111111111111").put("revision",7)
 @Test fun attentionRetainsTargetRevisionAndTrimsNote(){val command=CareCommands.attention(item(),"atender","  Aula revisada  ");assertEquals("aire_attention",command.name);assertEquals(7,command.arguments.getInt("p_revision"));assertEquals("Aula revisada",command.arguments.getString("p_note"))}
 @Test fun malformedActionsAndNotesNeverReachTransport(){assertThrows(IllegalArgumentException::class.java){CareCommands.attention(item(),"delete","valid note")};assertEquals("",CareCommands.attention(item(),"resolver","  ").arguments.getString("p_note"));assertThrows(IllegalArgumentException::class.java){CareCommands.respond(item(),"unknown","valid note")}}
 @Test fun retryRetainsInstructionId(){val command=CareCommands.issue(item(),"stable-id","Ventilar el aula","Variación comprobada",30);assertEquals("stable-id",command.arguments.getString("p_id"));assertEquals(7,command.arguments.getInt("p_revision"));assertThrows(IllegalArgumentException::class.java){CareCommands.issue(item(),"id","Ventilar","Motivo válido",121)}}
}
