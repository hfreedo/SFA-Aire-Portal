package org.sfa.aire.domain

enum class InboxFilter(val title:String){PENDING("Pendientes"),ATTENDED("Atendidos"),ARCHIVED("Archivo")}
object NoticeInbox {
 fun category(id:String,status:String,archived:Set<String>):InboxFilter =
  if(id in archived)InboxFilter.ARCHIVED else if(status=="resuelto")InboxFilter.ATTENDED else InboxFilter.PENDING
}
