package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.domain.ObservationState
class ObservationStateTest {
 private val now=java.time.Instant.parse("2026-10-25T12:00:00Z").toEpochMilli()
 @Test fun invalidTimestampIsStaleWithoutCrash(){val state=ObservationState.from("not-a-date","normal",now);assertFalse(state.fresh);assertEquals("sin_datos",state.state);assertNull(state.ageSeconds)}
 @Test fun freshBoundaryAndFutureClockAreExplicit(){for(seconds in listOf(-5,0,95))assertTrue(ObservationState.from(java.time.Instant.ofEpochMilli(now-seconds*1000).toString(),"normal",now).fresh);for(seconds in listOf(-6,96))assertFalse(ObservationState.from(java.time.Instant.ofEpochMilli(now-seconds*1000).toString(),"normal",now).fresh)}
 @Test fun fractionalSecondBeyondLimitIsStale(){assertFalse(ObservationState.from(java.time.Instant.ofEpochMilli(now-95001).toString(),"normal",now).fresh)}
 @Test fun ageUsesHumanUnitsWithoutHidingStaleness(){
  fun at(seconds:Long)=ObservationState.from(java.time.Instant.ofEpochMilli(now-seconds*1000).toString(),"alerta",now)
  assertEquals("Hace unos segundos",at(10).ageLabel)
  assertEquals("Hace 2 min",at(120).ageLabel)
  assertEquals("Hace 15 horas",at(57399).ageLabel)
  assertEquals("Hace 2 días",at(172800).ageLabel)
  assertFalse(at(57399).fresh);assertEquals("sin_datos",at(57399).state)
  assertTrue(at(-60).ageLabel.contains("adelantada"));assertFalse(at(-60).fresh)
 }
}
