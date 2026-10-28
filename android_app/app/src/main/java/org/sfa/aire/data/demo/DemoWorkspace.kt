package org.sfa.aire.data.demo
import android.content.Context
import org.json.JSONObject
import java.time.Instant

/** Fixture de lectura: no autentica, registra teléfonos ni ejecuta casos de uso. */
object DemoWorkspace {
    fun load(context:Context):JSONObject {
        val data=JSONObject(context.assets.open("demo-cloud.json").bufferedReader().use{it.readText()})
        val now=Instant.now()
        val snapshots=data.getJSONArray("snapshots")
        for(index in 0 until snapshots.length())snapshots.getJSONObject(index).put("sample_at",now.toString())
        val incidents=data.getJSONArray("incidents")
        for(index in 0 until incidents.length())incidents.getJSONObject(index).put("opened_at",now.minusSeconds(30).toString()).put("capabilities",JSONObject().put("can_attend",true).put("can_resolve",true).put("can_archive",false))
        for(index in 0 until incidents.length())incidents.getJSONObject(index)
            .put("trigger_sample_at",now.minusSeconds(30).toString())
            .put("trigger_observation",JSONObject().put("temperature",38).put("humidity",55).put("mq_raw",560).put("dht_ok",true).put("notification_test",true))
        val instructions=data.getJSONObject("coordination").getJSONArray("instructions")
        for(index in 0 until instructions.length())instructions.getJSONObject(index).put("expires_at",now.plusSeconds(1800).toString())
        return data
    }
}
