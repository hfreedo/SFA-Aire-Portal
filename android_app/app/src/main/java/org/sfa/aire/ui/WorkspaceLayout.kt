package org.sfa.aire.ui
import android.app.Activity
import android.graphics.Color
import android.os.Build
import android.view.View
import android.widget.*

/** Shell común de la aplicación Android: marca, estado, contenido y navegación. */
class WorkspaceLayout(activity:Activity,isDemo:()->Boolean,private val isBusy:()->Boolean){
    val root=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL}
    val ui=AireUi(activity,root,isDemo,isBusy)
    val status:TextView
    val nav:LinearLayout
    val scroll:ScrollView
    init {with(ui){
        activity.window.statusBarColor=Color.WHITE;activity.window.navigationBarColor=Color.WHITE
        activity.window.decorView.systemUiVisibility=View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        root.setPadding(dp(16),dp(14),dp(16),dp(20))
        val outer=column().apply{setBackgroundColor(page)}
        val brand=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL;setPadding(dp(20),dp(9),dp(20),dp(9));setBackgroundColor(page)}
        brand.addView(ImageView(activity).apply{setImageResource(org.sfa.aire.R.drawable.sfa_aire);contentDescription="SFA Aire"},LinearLayout.LayoutParams(dp(36),dp(36)))
        val brandText=column().apply{setPadding(dp(12),0,0,0)}
        text(brandText,"SFA Aire",20f,true)
        brand.addView(brandText);outer.addView(brand)
        status=text(outer,if(isDemo())"DEMOSTRACIÓN · Sin envíos reales" else "Acceso por cuenta y aula",14f)
        status.setPadding(dp(20),dp(7),dp(20),dp(7));status.setBackgroundColor(sage);status.accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE
        scroll=ScrollView(activity).apply{addView(root);isFillViewport=true}
        outer.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        nav=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;setPadding(dp(8),dp(8),dp(8),dp(8));setBackgroundColor(Color.WHITE)}
        outer.addView(nav);activity.setContentView(outer)
        outer.setOnApplyWindowInsetsListener{v,insets->if(Build.VERSION.SDK_INT>=30){val bars=insets.getInsets(android.view.WindowInsets.Type.systemBars());v.setPadding(0,bars.top,0,bars.bottom)};insets}
    }}
    fun navigation(page:String,onNavigate:(String)->Unit){with(ui){
        nav.removeAllViews();nav.visibility=View.VISIBLE
        for((id,title) in listOf("aula" to "Mi aula","incidentes" to "Avisos","ajustes" to "Ajustes")){
            val button=Button(activity).apply{text=title;isAllCaps=false;textSize=14f;typeface=android.graphics.Typeface.create("sans-serif-medium",0);setTextColor(green);background=shape(if(page==id)sage else Color.WHITE);stateListAnimator=null;elevation=0f;minHeight=dp(62);setPadding(dp(4),dp(7),dp(4),dp(7));compoundDrawablePadding=dp(3);setCompoundDrawablesWithIntrinsicBounds(null,AireIcon(activity,when(id){"aula"->"home";"incidentes"->"bell";else->"settings"},green,22),null,null);setOnClickListener{if(!isBusy())onNavigate(id)}}
            nav.addView(button,LinearLayout.LayoutParams(0,-2,1f).apply{marginStart=dp(3);marginEnd=dp(3)})
        }
    }}
}
