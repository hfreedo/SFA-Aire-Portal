package org.sfa.aire
import org.junit.Assert.*
import org.junit.Test
import org.sfa.aire.domain.NoticeInbox
import org.sfa.aire.domain.InboxFilter
class NoticeInboxTest {
 @Test fun archiveNeverResolvesSharedStatus(){val id="notice";assertEquals(InboxFilter.ARCHIVED,NoticeInbox.category(id,"pendiente",setOf(id)));assertEquals(InboxFilter.PENDING,NoticeInbox.category(id,"pendiente",emptySet()))}
 @Test fun resolvedGoesToAttendedAndCanBeArchived(){assertEquals(InboxFilter.ATTENDED,NoticeInbox.category("n","resuelto",emptySet()));assertEquals(InboxFilter.ARCHIVED,NoticeInbox.category("n","resuelto",setOf("n")))}
 @Test fun inAttentionStillPending(){assertEquals(InboxFilter.PENDING,NoticeInbox.category("n","en_atencion",emptySet()))}
}
