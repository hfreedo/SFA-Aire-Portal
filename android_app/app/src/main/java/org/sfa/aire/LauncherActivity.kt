package org.sfa.aire

import android.app.Activity
import android.content.Intent
import android.os.Bundle

/** Única entrada pública. Inicia navegación normal sin reenviar datos del remitente. */
class LauncherActivity:Activity() {
    override fun onCreate(savedInstanceState:Bundle?){
        super.onCreate(savedInstanceState)
        openWorkspace()
    }
    override fun onNewIntent(intent:Intent){super.onNewIntent(intent);openWorkspace()}
    private fun openWorkspace(){
        startActivity(Intent(this,CloudActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP))
        finish()
    }
}
