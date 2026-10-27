package org.sfa.aire.ui

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.content.res.ColorStateList
import android.animation.ValueAnimator
import android.view.View
import android.view.MotionEvent
import android.view.Gravity
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
        view.alpha=0f;view.translationY=dp(14).toFloat()
        view.animate().alpha(1f).translationY(0f).setDuration(280).setInterpolator(DecelerateInterpolator()).start()
    }
    fun pressFeedback(view:View){
        view.setOnTouchListener{v,event->
            if(v.isEnabled&&ValueAnimator.areAnimatorsEnabled())when(event.actionMasked){
                MotionEvent.ACTION_DOWN->v.animate().scaleX(.975f).scaleY(.975f).setDuration(90).start()
                MotionEvent.ACTION_UP,MotionEvent.ACTION_CANCEL->v.animate().scaleX(1f).scaleY(1f).setDuration(150).start()
            }
            false
        }
    }
    fun dialogBuilder(title:String):AlertDialog.Builder {
        val heading=column().apply{setPadding(dp(22),dp(20),dp(22),dp(8))}
        text(heading,title,21f,true)
        return AlertDialog.Builder(activity).setCustomTitle(heading)
    }
    fun styleDialog(dialog:AlertDialog){
        dialog.window?.apply{
            setBackgroundDrawable(shape(Color.WHITE));setDimAmount(.22f)
            setWindowAnimations(org.sfa.aire.R.style.AireDialogMotion)
            setLayout(minOf(activity.resources.displayMetrics.widthPixels-dp(32),dp(520)),-2)
        }
        for(id in listOf(AlertDialog.BUTTON_POSITIVE,AlertDialog.BUTTON_NEGATIVE,AlertDialog.BUTTON_NEUTRAL)){
            dialog.getButton(id)?.apply{
                isAllCaps=false;textSize=15f;minimumHeight=dp(48);stateListAnimator=null;elevation=0f
                surface(this,if(id==AlertDialog.BUTTON_POSITIVE)green else page,if(id==AlertDialog.BUTTON_POSITIVE)Color.WHITE else green)
                setPadding(dp(16),dp(8),dp(16),dp(8));pressFeedback(this)
            }
        }
    }
    fun choose(title:String,choices:List<String>,selected:Int,onChoose:(Int)->Unit):AlertDialog {
        val body=column().apply{setPadding(dp(14),dp(4),dp(14),dp(8))}
        lateinit var dialog:AlertDialog
        for((index,name) in choices.withIndex()){
            val row=button(body,name){dialog.dismiss();onChoose(index)}
            row.apply{
                isEnabled=true;alpha=1f;textSize=16f;gravity=Gravity.START or Gravity.CENTER_VERTICAL
                surface(this,if(index==selected)sage else page)
                contentDescription=name+if(index==selected)", seleccionada" else ""
                setCompoundDrawablesWithIntrinsicBounds(null,null,if(index==selected)AireIcon(activity,"check",green,22)else null,null)
                compoundDrawablePadding=dp(10);isSelected=index==selected
            }
        }
        val scroll=object:ScrollView(activity){override fun onMeasure(width:Int,height:Int){super.onMeasure(width,View.MeasureSpec.makeMeasureSpec((activity.resources.displayMetrics.heightPixels*.5f).toInt(),View.MeasureSpec.AT_MOST))}}.apply{addView(body);isFillViewport=false;clipToOutline=true}
        dialog=dialogBuilder(title).setView(scroll).setNegativeButton("Cancelar",null).create()
        dialog.show();styleDialog(dialog)
        return dialog
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
            styleField(this)
            inputType=if(passwordField)InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD else InputType.TYPE_CLASS_TEXT
            parent.addView(this,LinearLayout.LayoutParams(-1,dp(50)).apply{bottomMargin=dp(13)})}
    }
    fun styleField(field:EditText){
        field.setTextColor(ink);field.setHintTextColor(muted)
        field.background=android.graphics.drawable.StateListDrawable().apply{
            addState(intArrayOf(android.R.attr.state_focused),shape(Color.WHITE,green))
            addState(intArrayOf(),shape(page,sageStrong))
        }
    }
    fun styleSwitch(control:Switch){
        control.showText=false;control.splitTrack=false;control.switchMinWidth=dp(48);control.switchPadding=dp(12)
        control.thumbDrawable=GradientDrawable().apply{shape=GradientDrawable.OVAL;setColor(Color.WHITE);setSize(dp(24),dp(24));setStroke(dp(1),Color.rgb(214,222,210))}
        control.trackDrawable=GradientDrawable().apply{cornerRadius=dp(15).toFloat();setColor(green);setSize(dp(48),dp(28))}
        control.trackTintList=ColorStateList(arrayOf(intArrayOf(android.R.attr.state_enabled,android.R.attr.state_checked),intArrayOf(android.R.attr.state_enabled),intArrayOf()),intArrayOf(green,Color.rgb(211,220,205),Color.rgb(225,231,220)))
        control.thumbTintList=ColorStateList.valueOf(Color.WHITE)
    }
    fun button(parent:LinearLayout,title:String,action:()->Unit):Button=Button(activity).apply{
        text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL);surface(this,green,Color.WHITE);stateListAnimator=null;elevation=0f;minimumHeight=dp(48);setPadding(dp(14),dp(8),dp(14),dp(8))
        parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{topMargin=dp(8);bottomMargin=dp(3)})
        isEnabled=!isDemo();alpha=if(isDemo())0.45f else 1f;setOnClickListener{if(!isBusy())action()}
        pressFeedback(this)
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
        val header=FrameLayout(activity);wrapper.addView(header,LinearLayout.LayoutParams(-1,-2))
        val toggle=Button(activity).apply{
            text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",0)
            minimumHeight=dp(48);stateListAnimator=null;elevation=0f;gravity=Gravity.START or Gravity.CENTER_VERTICAL
            setPadding(dp(12),dp(8),dp(44),dp(8));surface(this,page);pressFeedback(this)
        }
        header.addView(toggle,FrameLayout.LayoutParams(-1,-2))
        val arrow=ImageView(activity).apply{setImageDrawable(AireIcon(activity,"chevron",green,20));importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO;isClickable=false}
        header.addView(arrow,FrameLayout.LayoutParams(dp(20),dp(20),Gravity.END or Gravity.CENTER_VERTICAL).apply{marginEnd=dp(13)})
        toggle.isEnabled=true;toggle.alpha=1f
        wrapper.addView(body,LinearLayout.LayoutParams(-1,-2))
        var expanded=disclosures[key]?:false;var moving=false
        fun label(){toggle.contentDescription=title+if(expanded)", expandido" else ", contraído"}
        body.visibility=if(expanded)View.VISIBLE else View.GONE;label()
        arrow.rotation=if(expanded)180f else 0f
        toggle.setOnClickListener{
            if(moving)return@setOnClickListener
            expanded=!expanded;disclosures[key]=expanded;label()
            if(!ValueAnimator.areAnimatorsEnabled()){body.alpha=1f;body.visibility=if(expanded)View.VISIBLE else View.GONE;arrow.rotation=if(expanded)180f else 0f;return@setOnClickListener}
            arrow.animate().rotation(if(expanded)180f else 0f).setDuration(260).start()
            body.alpha=if(expanded)0f else 1f;body.animate().alpha(if(expanded)1f else 0f).setDuration(240).start()
            val width=(wrapper.width.takeIf{it>0}?:activity.resources.displayMetrics.widthPixels-dp(64))
            body.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
            val height=body.measuredHeight
            moving=true;body.visibility=View.VISIBLE
            ValueAnimator.ofInt(if(expanded)0 else height,if(expanded)height else 0).apply{
                duration=260;interpolator=DecelerateInterpolator()
                addUpdateListener{body.layoutParams=body.layoutParams.apply{this.height=it.animatedValue as Int}}
                addListener(object:android.animation.AnimatorListenerAdapter(){override fun onAnimationEnd(animation:android.animation.Animator){
                    body.layoutParams=body.layoutParams.apply{this.height=-2};body.visibility=if(expanded)View.VISIBLE else View.GONE;body.alpha=1f;moving=false
                }})
                start()
            }
        }
    }
}
