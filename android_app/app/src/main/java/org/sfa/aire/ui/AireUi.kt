package org.sfa.aire.ui

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.content.res.ColorStateList
import android.animation.ValueAnimator
import android.view.View
import android.view.animation.DecelerateInterpolator
import android.text.InputType
import android.widget.*

/** Componentes visuales compartidos; sin sesión, transporte ni reglas de negocio. */
class AireUi(val activity:Activity,val root:LinearLayout,private val isDemo:()->Boolean,private val isBusy:()->Boolean){
    val ink=Color.rgb(37,55,43)
    val green=Color.rgb(51,82,58)
    val muted=Color.rgb(64,83,66)
    val sage=Color.rgb(218,229,209)
    val sageStrong=Color.rgb(191,210,180)
    val page=Color.rgb(245,247,239)
    val disclosures=mutableMapOf<String,Boolean>()
    fun dp(n:Int)=(n*activity.resources.displayMetrics.density).toInt()
    fun shape(color:Int,border:Int=Color.TRANSPARENT)=GradientDrawable().apply{setColor(color);cornerRadius=dp(18).toFloat();setStroke(dp(1),border)}
    fun surface(button:Button,color:Int,foreground:Int=green){
        button.setTextColor(foreground)
        button.background=RippleDrawable(ColorStateList.valueOf(Color.argb(35,51,82,58)),shape(color),shape(Color.WHITE))
    }
    fun enter(view:View){
        view.animate().cancel()
        if(!ValueAnimator.areAnimatorsEnabled()){view.alpha=1f;view.translationY=0f;return}
        view.alpha=.2f;view.translationY=dp(6).toFloat()
        view.animate().alpha(1f).translationY(0f).setDuration(200).setInterpolator(DecelerateInterpolator()).start()
    }
    fun column()=LinearLayout(activity).apply{orientation=LinearLayout.VERTICAL}
    fun text(parent:LinearLayout,value:String,size:Float=16f,bold:Boolean=false):TextView=TextView(activity).apply{
        text=value;textSize=maxOf(14f,size);setTextColor(if(size<=14f)muted else ink);setPadding(0,dp(3),0,dp(3));setLineSpacing(dp(2).toFloat(),1f)
        typeface=Typeface.create("sans-serif",if(bold)Typeface.BOLD else Typeface.NORMAL);parent.addView(this)
    }
    fun meta(parent:LinearLayout,label:String,value:String){
        val row=LinearLayout(activity).apply{orientation=LinearLayout.HORIZONTAL}
        parent.addView(row,LinearLayout.LayoutParams(-1,-2))
        text(row,label,14f).layoutParams=LinearLayout.LayoutParams(0,-2,1.35f)
        text(row,value,14f,true).layoutParams=LinearLayout.LayoutParams(0,-2,1.65f)
    }
    fun input(parent:LinearLayout,label:String,value:String,passwordField:Boolean=false):EditText {
        text(parent,label,15f,true)
        return EditText(activity).apply{setText(value);hint=label;textSize=16f;isSingleLine=true;setTextColor(ink);setPadding(dp(12),dp(9),dp(12),dp(9));background=shape(Color.WHITE)
            inputType=if(passwordField)InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD else InputType.TYPE_CLASS_TEXT
            parent.addView(this,LinearLayout.LayoutParams(-1,dp(50)).apply{bottomMargin=dp(13)})}
    }
    fun button(parent:LinearLayout,title:String,action:()->Unit):Button=Button(activity).apply{
        text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL);surface(this,green,Color.WHITE);stateListAnimator=null;elevation=0f;minimumHeight=dp(48);setPadding(dp(14),dp(8),dp(14),dp(8))
        parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{topMargin=dp(8);bottomMargin=dp(3)})
        isEnabled=!isDemo();alpha=if(isDemo())0.45f else 1f;setOnClickListener{if(!isBusy())action()}
    }
    fun actionButton(parent:LinearLayout,title:String,allowed:Boolean,action:()->Unit):Button=button(parent,title,action).apply{isEnabled=isEnabled&&allowed;alpha=if(isEnabled)1f else .45f}
    fun secondary(parent:LinearLayout,title:String,action:()->Unit):Button=button(parent,title,action).apply{surface(this,sage)}
    fun card(parent:LinearLayout=root,color:Int=Color.WHITE):LinearLayout=column().apply{
        background=shape(color,if(color==Color.WHITE)Color.rgb(227,233,223)else Color.TRANSPARENT);setPadding(dp(16),dp(13),dp(16),dp(13));parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(12)})}
    fun badge(parent:LinearLayout,value:String,color:Int=sage):TextView=TextView(activity).apply{
        text=value;textSize=12f;typeface=Typeface.create("sans-serif-medium",0);setTextColor(ink);background=shape(color)
        setPadding(dp(9),dp(4),dp(9),dp(4));parent.addView(this,LinearLayout.LayoutParams(-2,-2).apply{marginEnd=dp(6);bottomMargin=dp(6)})
    }
    fun disclosure(parent:LinearLayout,title:String,key:String,content:(LinearLayout)->Unit){
        val wrapper=column();parent.addView(wrapper,LinearLayout.LayoutParams(-1,-2))
        val body=column();content(body)
        val toggle=secondary(wrapper,title){}
        toggle.isEnabled=true;toggle.alpha=1f
        wrapper.addView(body,LinearLayout.LayoutParams(-1,-2))
        var expanded=disclosures[key]?:false;var moving=false
        fun label(){toggle.text=title+if(expanded)"  −" else "  +";toggle.contentDescription=title+if(expanded)", expandido" else ", contraído"}
        body.visibility=if(expanded)View.VISIBLE else View.GONE;label()
        toggle.setOnClickListener{
            if(moving)return@setOnClickListener
            expanded=!expanded;disclosures[key]=expanded;label()
            if(!ValueAnimator.areAnimatorsEnabled()){body.visibility=if(expanded)View.VISIBLE else View.GONE;return@setOnClickListener}
            val width=(wrapper.width.takeIf{it>0}?:activity.resources.displayMetrics.widthPixels-dp(64))
            body.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
            val height=body.measuredHeight
            moving=true;body.visibility=View.VISIBLE
            ValueAnimator.ofInt(if(expanded)0 else height,if(expanded)height else 0).apply{
                duration=180;interpolator=DecelerateInterpolator()
                addUpdateListener{body.layoutParams=body.layoutParams.apply{this.height=it.animatedValue as Int}}
                addListener(object:android.animation.AnimatorListenerAdapter(){override fun onAnimationEnd(animation:android.animation.Animator){
                    body.layoutParams=body.layoutParams.apply{this.height=-2};body.visibility=if(expanded)View.VISIBLE else View.GONE;moving=false
                }})
                start()
            }
        }
    }
}
