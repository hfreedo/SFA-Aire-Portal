package org.sfa.aire.data.session

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import org.json.JSONObject

/** Cifrado autenticado común; cada repositorio usa alias y propósito propios. */
internal class KeystoreCipher(private val alias:String,purpose:String) {
    private val aad=purpose.toByteArray(Charsets.UTF_8)
    fun encrypt(value:String):String {
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE,key());cipher.updateAAD(aad)
        return JSONObject().put("v",1).put("iv",Base64.getEncoder().encodeToString(cipher.iv))
            .put("data",Base64.getEncoder().encodeToString(cipher.doFinal(value.toByteArray(Charsets.UTF_8)))).toString()
    }
    fun decrypt(encoded:String):String {
        require(encoded.length<=65536)
        val envelope=JSONObject(encoded);require(envelope.getInt("v")==1)
        val iv=Base64.getDecoder().decode(envelope.getString("iv"));require(iv.size==12)
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,iv));cipher.updateAAD(aad)
        return String(cipher.doFinal(Base64.getDecoder().decode(envelope.getString("data"))),Charsets.UTF_8)
    }
    private fun key():SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply{load(null)}
        (store.getKey(alias,null) as? SecretKey)?.let{return it}
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply{
            init(KeyGenParameterSpec.Builder(alias,KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true).build())
        }.generateKey()
    }
}
