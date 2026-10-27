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
    val nav:FrameLayout
    private var selectedTab=""
    private var navigate:((String)->Unit)?=null
    private val tabViews=mutableMapOf<String,Pair<LinearLayout,TextView>>()
    private lateinit var indicator:View
    private var indicatorPositioned=false
    val scroll:ScrollView
    init {with(ui){
        activity.window.statusBarColor=Color.WHITE;activity.window.navigationBarColor=Color.WHITE
        activity.window.decorView.systemUiVisibility=View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        root.setPadding(dp(16),dp(16),dp(16),dp(16))
        val outer=column().apply{setBackgroundColor(page)}
        val brand=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL;gravity=android.view.Gravity.CENTER_VERTICAL;setPadding(dp(16),dp(10),dp(16),dp(4));setBackgroundColor(page)}
        brand.addView(ImageView(activity).apply{setImageResource(org.sfa.aire.R.drawable.sfa_aire);importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(28),dp(28)))
        val brandText=column().apply{setPadding(dp(12),0,0,0)}
        text(brandText,"SFA Aire",18f,true)
        brand.addView(brandText);outer.addView(brand)
        status=text(outer,if(isDemo())"Demostración · Sin envíos reales" else "Acceso por cuenta y aula",14f)
        status.setPadding(dp(16),0,dp(16),dp(5));status.setBackgroundColor(page);status.accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE
        scroll=ScrollView(activity).apply{addView(root);isFillViewport=true;isSmoothScrollingEnabled=true;clipToPadding=false}
        outer.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        nav=FrameLayout(activity).apply{setPadding(dp(8),dp(5),dp(8),dp(5));setBackgroundColor(Color.WHITE)}
        outer.addView(nav);activity.setContentView(outer)
        outer.setOnApplyWindowInsetsListener{v,insets->if(Build.VERSION.SDK_INT>=30){val bars=insets.getInsets(android.view.WindowInsets.Type.systemBars());v.setPadding(0,bars.top,0,bars.bottom)};insets}
    }}
    fun cancelTransition(){scroll.animate().cancel();scroll.alpha=1f;scroll.translationX=0f}
    fun transition(direction:Int,change:()->Unit,finished:()->Unit){
        cancelTransition()
        if(!android.animation.ValueAnimator.areAnimatorsEnabled()){change();finished();return}
        scroll.animate().alpha(0f).translationX(-direction*ui.dp(6).toFloat()).setDuration(60).withEndAction{
            change()
            scroll.alpha=0f;scroll.translationX=direction*ui.dp(10).toFloat()
            scroll.animate().alpha(1f).translationX(0f).setDuration(180).setInterpolator(android.view.animation.DecelerateInterpolator()).withEndAction{finished()}.start()
        }.start()
    }
    private fun positionIndicator(animate:Boolean){with(ui){
        if(nav.width==0)return
        val index=listOf("aula","incidentes","ajustes").indexOf(selectedTab).coerceAtLeast(0)
        val available=nav.width-nav.paddingLeft-nav.paddingRight
        val x=index*available/3f+(available/3f-dp(56))/2f
        indicator.translationY=tabViews[selectedTab]?.first?.getChildAt(0)?.top?.toFloat()?:0f
        indicator.animate().cancel()
        if(animate&&indicatorPositioned&&android.animation.ValueAnimator.areAnimatorsEnabled())indicator.animate().translationX(x).setDuration(220).setInterpolator(android.view.animation.AccelerateDecelerateInterpolator()).start()
        else indicator.translationX=x
        indicatorPositioned=true
    }}
    fun navigation(page:String,onNavigate:(String)->Unit){with(ui){
        navigate=onNavigate;nav.visibility=View.VISIBLE
        if(tabViews.isEmpty()){
            indicator=View(activity).apply{background=shape(sage);importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO}
            nav.addView(indicator,FrameLayout.LayoutParams(dp(56),dp(29)).apply{topMargin=0})
            val row=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL}
            nav.addView(row,FrameLayout.LayoutParams(-1,-2))
            for((id,title) in listOf("aula" to "Mi aula","incidentes" to "Avisos","ajustes" to "Ajustes")){
                val item=column().apply{gravity=android.view.Gravity.CENTER;minimumHeight=dp(58);isClickable=true;isFocusable=true;contentDescription=title;importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_YES}
                val icon=ImageView(activity).apply{setImageDrawable(AireIcon(activity,when(id){"aula"->"home";"incidentes"->"bell";else->"settings"},green,21));setPadding(dp(16),dp(3),dp(16),dp(3));importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO}
                item.addView(icon,LinearLayout.LayoutParams(dp(56),dp(29)))
                val label=TextView(activity).apply{text=title;textSize=12f;setTextColor(green);gravity=android.view.Gravity.CENTER;importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO}
                item.addView(label,LinearLayout.LayoutParams(-1,-2));pressFeedback(item)
                item.setOnClickListener{if(!isBusy()&&selectedTab!=id)navigate?.invoke(id)}
                row.addView(item,LinearLayout.LayoutParams(0,-2,1f));tabViews[id]=item to label
            }
            nav.addOnLayoutChangeListener{_,left,_,right,_,oldLeft,_,oldRight,_->if(right-left!=oldRight-oldLeft||!indicatorPositioned)positionIndicator(false)}
        }
        val changed=selectedTab!=page;selectedTab=page
        for((id,pair) in tabViews){pair.first.isSelected=id==page;pair.second.typeface=android.graphics.Typeface.create(if(id==page)"sans-serif-medium" else "sans-serif",0)}
        if(changed){
            nav.viewTreeObserver.addOnPreDrawListener(object:android.view.ViewTreeObserver.OnPreDrawListener{
                override fun onPreDraw():Boolean {
                    nav.viewTreeObserver.removeOnPreDrawListener(this)
                    positionIndicator(true)
                    return true
                }
            })
            nav.invalidate()
        }
    }}
}
