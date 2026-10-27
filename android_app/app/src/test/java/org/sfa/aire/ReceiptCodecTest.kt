package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.data.notifications.ReceiptCodec
class ReceiptCodecTest {
 private val id="11111111-1111-4111-8111-111111111111"
 @Test fun cloudReceiptRetainsGeneration(){val encoded=ReceiptCodec.encode("cloud",id,"abierto",4)!!;assertEquals(4L,ReceiptCodec.decode(encoded)!!.generation);assertEquals("cloud",ReceiptCodec.decode(encoded)!!.route)}
 @Test fun neverReassignsLegacyCloudReceipt(){assertNull(ReceiptCodec.decode("cloud|$id|recibido"));assertNull(ReceiptCodec.decode("cloud@4|$id|recibido"));assertNull(ReceiptCodec.encode("cloud",id,"recibido"))}
 @Test fun localReceiptRetainsConnectionGeneration(){
  val encoded=ReceiptCodec.encode("local",id,"recibido",8,id,id)!!
  assertEquals("local3@8|$id|$id|$id|recibido",encoded);assertEquals(id,ReceiptCodec.decode(encoded)!!.receiverId);assertEquals(id,ReceiptCodec.decode(encoded)!!.binding);assertEquals(8L,ReceiptCodec.decode(encoded)!!.generation)
  assertEquals("local",ReceiptCodec.decode(encoded)!!.route)
 }
 @Test fun neverCreatesUnboundNewLocalReceipt(){assertNull(ReceiptCodec.encode("local",id,"abierto"));assertNull(ReceiptCodec.decode("local2@-1|$id|recibido"))}
 @Test fun preservesLegacyLanReceipt(){assertEquals("local",ReceiptCodec.decode("$id|recibido")!!.route)}
 @Test fun rejectsMalformedReceiptAndPathInjection(){for(value in listOf("", "cloud2@bad|$id|recibido", "cloud2@-1|$id|abierto", "local|../secret|abierto", "local|$id|resolver", "other|$id|recibido"))assertNull(ReceiptCodec.decode(value));assertNull(ReceiptCodec.encode("local","1-1-1-1-1","abierto"))}
}
