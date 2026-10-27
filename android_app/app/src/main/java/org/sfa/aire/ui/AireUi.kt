package org.sfa.aire.ui

import android.app.Activity
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
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
    fun dp(n:Int)=(n*activity.resources.displayMetrics.density).toInt()
    fun shape(color:Int,border:Int=Color.TRANSPARENT)=GradientDrawable().apply{setColor(color);cornerRadius=dp(24).toFloat();setStroke(dp(1),border)}
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
        text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL);setTextColor(Color.WHITE);background=shape(green,green);stateListAnimator=null;elevation=0f;minimumHeight=dp(48);setPadding(dp(14),dp(10),dp(14),dp(10))
        parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{topMargin=dp(8);bottomMargin=dp(3)})
        isEnabled=!isDemo();alpha=if(isDemo())0.45f else 1f;setOnClickListener{if(!isBusy())action()}
    }
    fun actionButton(parent:LinearLayout,title:String,allowed:Boolean,action:()->Unit):Button=button(parent,title,action).apply{isEnabled=isEnabled&&allowed;alpha=if(isEnabled)1f else .45f}
    fun secondary(parent:LinearLayout,title:String,action:()->Unit):Button=button(parent,title,action).apply{setTextColor(green);background=shape(sage)}
    fun card(parent:LinearLayout=root,color:Int=Color.WHITE):LinearLayout=column().apply{
        background=shape(color);setPadding(dp(19),dp(16),dp(19),dp(16));parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(14)})}
}
