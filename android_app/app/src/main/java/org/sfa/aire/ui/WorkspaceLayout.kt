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
        root.setPadding(dp(16),dp(10),dp(16),dp(16))
        val outer=column().apply{setBackgroundColor(page)}
        val brand=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL;setPadding(dp(16),dp(6),dp(16),dp(4));setBackgroundColor(page)}
        brand.addView(ImageView(activity).apply{setImageResource(org.sfa.aire.R.drawable.sfa_aire);importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(28),dp(28)))
        val brandText=column().apply{setPadding(dp(12),0,0,0)}
        text(brandText,"SFA Aire",18f,true)
        brand.addView(brandText);outer.addView(brand)
        status=text(outer,if(isDemo())"Demostración · Sin envíos reales" else "Acceso por cuenta y aula",14f)
        status.setPadding(dp(16),0,dp(16),dp(5));status.setBackgroundColor(page);status.accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE
        scroll=ScrollView(activity).apply{addView(root);isFillViewport=true;isSmoothScrollingEnabled=true;clipToPadding=false}
        outer.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        nav=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;setPadding(dp(8),dp(5),dp(8),dp(5));setBackgroundColor(Color.WHITE)}
        outer.addView(nav);activity.setContentView(outer)
        outer.setOnApplyWindowInsetsListener{v,insets->if(Build.VERSION.SDK_INT>=30){val bars=insets.getInsets(android.view.WindowInsets.Type.systemBars());v.setPadding(0,bars.top,0,bars.bottom)};insets}
    }}
    fun navigation(page:String,onNavigate:(String)->Unit){with(ui){
        nav.removeAllViews();nav.visibility=View.VISIBLE
        for((id,title) in listOf("aula" to "Mi aula","incidentes" to "Avisos","ajustes" to "Ajustes")){
            val selected=page==id
            val item=column().apply{gravity=android.view.Gravity.CENTER;minimumHeight=dp(58);isClickable=true;isFocusable=true;isSelected=selected;contentDescription=title;importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_YES}
            val icon=ImageView(activity).apply{setImageDrawable(AireIcon(activity,when(id){"aula"->"home";"incidentes"->"bell";else->"settings"},green,21));setPadding(dp(16),dp(3),dp(16),dp(3));background=shape(if(selected)sage else Color.WHITE);importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO}
            item.addView(icon,LinearLayout.LayoutParams(dp(56),dp(29)))
            item.addView(TextView(activity).apply{text=title;textSize=12f;setTextColor(green);typeface=android.graphics.Typeface.create(if(selected)"sans-serif-medium" else "sans-serif",0);gravity=android.view.Gravity.CENTER;importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(-1,-2))
            item.setOnClickListener{if(!isBusy()&&!selected)onNavigate(id)}
            nav.addView(item,LinearLayout.LayoutParams(0,-2,1f))
        }
    }}
}
