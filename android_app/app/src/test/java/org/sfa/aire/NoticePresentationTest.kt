package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.domain.NoticePresentation
class NoticePresentationTest {
 @Test fun severityAndSourceAreExplicit(){
  assertEquals("Alerta simulada",NoticePresentation.title("simulacion","alerta"))
  assertEquals("Aviso simulado",NoticePresentation.title("simulacion","aviso"))
  assertEquals("Alerta del aula",NoticePresentation.title("arduino","alerta"))
  assertEquals("Aviso atendido",NoticePresentation.title("simulacion","alerta",true))
 }
 @Test fun missingAndInvalidNeverBecomeZero(){for(v in listOf(null,Double.NaN,Double.POSITIVE_INFINITY,-1.0,1024.0))assertEquals("No disponible",NoticePresentation.measurement(v,0.0,1023.0,"ADC"))}
 @Test fun adcIsExplicitAndNeverConverted(){assertEquals("600 ADC",NoticePresentation.measurement(600.0,0.0,1023.0,"ADC"));assertTrue(NoticePresentation.measurement(38.0,-40.0,125.0,"°C",1).endsWith(" °C"))}
}
