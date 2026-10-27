package org.sfa.aire.data.network

import java.net.HttpURLConnection
import java.net.URL
import java.io.ByteArrayOutputStream
import org.json.JSONObject

class HttpFailure(val status:Int,message:String):IllegalStateException(message)

/** Transporte compartido por LAN y cloud: límites, cierre y ninguna redirección. */
object JsonTransport {
    const val MAX_RESPONSE_BYTES=2*1024*1024
    fun request(url:String,method:String,headers:Map<String,String>,body:JSONObject?=null,errorField:String="message"):JSONObject {
        val connection=URL(url).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout=8000
            connection.readTimeout=8000
            connection.instanceFollowRedirects=false
            connection.requestMethod=method
            headers.forEach{(name,value)->connection.setRequestProperty(name,value)}
            if(body!=null){
                val bytes=body.toString().toByteArray(Charsets.UTF_8)
                require(bytes.size<=512*1024){"La solicitud supera el tamaño permitido"}
                connection.doOutput=true
                connection.setRequestProperty("Content-Type","application/json")
                connection.outputStream.use{it.write(bytes)}
            }
            val code=connection.responseCode
            check(code !in 300..399){"La conexión respondió con una redirección. Revise la dirección configurada."}
            val stream=if(code in 200..299)connection.inputStream else connection.errorStream
            val bytes=stream?.use{input->
                val result=ByteArrayOutputStream()
                val buffer=ByteArray(8192)
                while(result.size()<=MAX_RESPONSE_BYTES){
                    val count=input.read(buffer,0,minOf(buffer.size,MAX_RESPONSE_BYTES+1-result.size()))
                    if(count<0)break
                    result.write(buffer,0,count)
                }
                result.toByteArray()
            }?:ByteArray(0)
            check(bytes.size<=MAX_RESPONSE_BYTES){"La respuesta supera el tamaño permitido"}
            val text=String(bytes,Charsets.UTF_8)
            if(code !in 200..299){
                val message=try{JSONObject(text).optString(errorField,"HTTP $code")}catch(_:Exception){"HTTP $code"}
                throw HttpFailure(code,message.take(1000))
            }
            return CloudReply.parse(text)
        } finally { connection.disconnect() }
    }
}
