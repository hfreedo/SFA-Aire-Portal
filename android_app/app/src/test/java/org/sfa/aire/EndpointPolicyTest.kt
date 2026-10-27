package org.sfa.aire
import org.sfa.aire.data.network.*
import org.junit.Assert.*
import org.junit.Test
import java.util.Base64

class EndpointPolicyTest {
    private fun jwt(role:String)="eyJhbGciOiJIUzI1NiJ9."+Base64.getUrlEncoder().withoutPadding().encodeToString("{\"role\":\"$role\"}".toByteArray())+".fixture"
    @Test fun acceptsPublicConfiguration(){assertEquals("https://example.supabase.co",EndpointPolicy.cloud("https://example.supabase.co/","sb_publishable_fixture"));EndpointPolicy.cloud("https://example.supabase.co",jwt("anon"))}
    @Test fun rejectsPrivilegedKeysAtTransportBoundary(){for(key in listOf("sb_secret_fixture",jwt("service_role"),jwt("authenticated"),"eyJinvalid")){assertThrows(IllegalArgumentException::class.java){EndpointPolicy.cloud("https://example.supabase.co",key)}}}
    @Test fun rejectsCredentialsPathsAndParameters(){for(url in listOf("https://user:password@example.test","https://example.test/path","https://example.test?key=value","https://example.test#fragment","http://example.test","https://example.test:0")){assertThrows(IllegalArgumentException::class.java){EndpointPolicy.cloud(url,"sb_publishable_fixture")}}}
    @Test fun cleartextOnlyForPrivateLiteralAddress(){for(host in listOf("192.168.1.3","10.0.0.1","172.16.0.2","172.31.0.1","127.0.0.1","localhost","[::1]"))assertEquals("http://$host:8766",EndpointPolicy.local("http://$host:8766"));for(host in listOf("example.test","8.8.8.8","172.32.0.1","192.169.0.1","192.168.0.999")){assertThrows(IllegalArgumentException::class.java){EndpointPolicy.local("http://$host")}}}
}
