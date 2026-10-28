package org.sfa.aire.data.inbox
import android.content.Context
import java.security.MessageDigest
import java.util.UUID

/** Organización personal en este dispositivo; no resuelve ni elimina incidentes cloud. */
class NoticeInboxRepository(context:Context){
 private val prefs=context.getSharedPreferences("sfa-aire-inbox",Context.MODE_PRIVATE)
 private fun key(owner:String):String {
  require(UUID.fromString(owner).toString()==owner){"Cuenta no verificable"}
  return "archived-"+MessageDigest.getInstance("SHA-256").digest(owner.toByteArray()).joinToString(""){"%02x".format(it)}
 }
 fun archived(owner:String):Set<String> = prefs.getStringSet(key(owner),emptySet())!!.toSet()
 fun setArchived(owner:String,id:String,archive:Boolean){
  require(UUID.fromString(id).toString()==id){"Aviso no verificable"}
  val values=archived(owner).toMutableSet()
  if(archive){check(values.size<500||id in values){"El archivo local está lleno. Restaura avisos antes de añadir más."};values.add(id)}else values.remove(id)
  check(prefs.edit().putStringSet(key(owner),values).commit()){"No se pudo guardar el archivo local"}
 }
}
