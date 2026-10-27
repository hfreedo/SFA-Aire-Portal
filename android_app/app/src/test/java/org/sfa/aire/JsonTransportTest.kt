package org.sfa.aire
import org.sfa.aire.data.network.*
import org.junit.Assert.*
import org.junit.Test
import java.net.ServerSocket
import java.net.InetAddress
import java.util.concurrent.CopyOnWriteArrayList

class JsonTransportTest {
    private class Server(val code:Int,val body:ByteArray,val redirect:Boolean=false):AutoCloseable {
        val socket=ServerSocket(0,4,InetAddress.getByName("127.0.0.1"))
        val base="http://127.0.0.1:${socket.localPort}"
        val requests=CopyOnWriteArrayList<String>()
        private val thread=Thread{
            while(!socket.isClosed){try{socket.accept().use{client->
                client.soTimeout=3000
                val input=client.getInputStream().bufferedReader()
                requests.add(input.readLine()?:"")
                while(true){val line=input.readLine();if(line==null||line.isEmpty())break}
                val location=if(redirect)"Location: $base/target\r\n" else ""
                val headers="HTTP/1.1 $code Fixture\r\nContent-Length: ${body.size}\r\n${location}Connection: close\r\n\r\n"
                client.getOutputStream().apply{write(headers.toByteArray());write(body);flush()}
            }}catch(_:Exception){if(socket.isClosed)break}}
        }.apply{isDaemon=true;start()}
        override fun close(){socket.close();thread.join(1000)}
    }
    @Test fun neverFollowsRedirectWithCredential(){Server(302,ByteArray(0),true).use{s->assertThrows(IllegalStateException::class.java){JsonTransport.request(s.base+"/redirect","GET",mapOf("Authorization" to "Bearer fixture-only"))};assertEquals(1,s.requests.size);assertFalse(s.requests.any{it.contains("/target")})}}
    @Test fun rejectsOversizedResponse(){Server(200,ByteArray(JsonTransport.MAX_RESPONSE_BYTES+1){32}).use{s->assertThrows(IllegalStateException::class.java){JsonTransport.request(s.base+"/large","GET",emptyMap())}}}
    @Test fun preservesLocalActionError(){Server(409,"{\"detail\":\"Falta recuperación comprobada\"}".toByteArray()).use{s->val error=assertThrows(IllegalStateException::class.java){JsonTransport.request(s.base+"/error","POST",emptyMap(),errorField="detail")};assertEquals("Falta recuperación comprobada",error.message);assertEquals(409,(error as HttpFailure).status)}}
    @Test fun preservesCloudScalarRpc(){Server(200,"\"uuid-fixture\"".toByteArray()).use{s->assertEquals("uuid-fixture",JsonTransport.request(s.base+"/scalar","POST",emptyMap()).getString("result"))}}
}
