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
    val ink=Color.rgb(36,48,57)
    val green=Color.rgb(37,109,91)
    val muted=Color.rgb(82,98,111)
    val sage=Color.rgb(229,240,235)
    val sageStrong=Color.rgb(216,224,228)
    val outline=sageStrong
    val controlOutline=Color.rgb(130,146,157)
    val page=Color.rgb(244,246,248)
    val simulationSurface=Color.rgb(240,236,247)
    val simulationInk=Color.rgb(105,83,133)
    val warningSurface=Color.rgb(255,244,223)
    val warningInk=Color.rgb(128,83,22)
    val alertSurface=Color.rgb(250,235,229)
    val alertInk=Color.rgb(151,67,48)
    val neutralSurface=Color.rgb(237,241,244)
    val locale=java.util.Locale.forLanguageTag("es-PY")
    fun sensorColor(kind:String)=when(kind){"temperature"->Color.rgb(151,83,38);"humidity"->Color.rgb(48,103,145);else->Color.rgb(38,109,103)}
    fun sensorSurface(kind:String)=when(kind){"temperature"->Color.rgb(255,241,230);"humidity"->Color.rgb(232,241,249);else->Color.rgb(230,243,239)}
    val disclosures=mutableMapOf<String,Boolean>()
    fun dp(n:Int)=(n*activity.resources.displayMetrics.density).toInt()
    fun shape(color:Int,border:Int=Color.TRANSPARENT,radius:Int=16)=GradientDrawable().apply{setColor(color);cornerRadius=dp(radius).toFloat();setStroke(dp(1),border)}
    fun surface(button:Button,color:Int,foreground:Int=green){
        val disabled=Color.rgb(112,125,135)
        button.setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf()),intArrayOf(disabled,foreground)))
        button.background=android.graphics.drawable.StateListDrawable().apply{
            addState(intArrayOf(-android.R.attr.state_enabled),shape(if(color==Color.TRANSPARENT)Color.TRANSPARENT else neutralSurface,if(color==Color.TRANSPARENT)Color.TRANSPARENT else outline,10))
            addState(intArrayOf(),RippleDrawable(ColorStateList.valueOf(Color.argb(30,37,109,91)),shape(color,if(color==Color.WHITE)controlOutline else Color.TRANSPARENT,10),shape(Color.WHITE,radius=10)))
        }
    }
    fun enter(view:View){
        view.animate().cancel()
        if(!ValueAnimator.areAnimatorsEnabled()){view.alpha=1f;view.translationY=0f;return}
        view.alpha=0f;view.translationY=dp(14).toFloat()
        view.animate().alpha(1f).translationY(0f).setDuration(200).setInterpolator(DecelerateInterpolator()).start()
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
            setBackgroundDrawable(shape(Color.WHITE,radius=20));setDimAmount(.22f)
            setWindowAnimations(org.sfa.aire.R.style.AireDialogMotion)
            setLayout(minOf(activity.resources.displayMetrics.widthPixels-dp(32),dp(520)),-2)
        }
        for(id in listOf(AlertDialog.BUTTON_POSITIVE,AlertDialog.BUTTON_NEGATIVE,AlertDialog.BUTTON_NEUTRAL)){
            dialog.getButton(id)?.apply{
                isAllCaps=false;textSize=15f;minimumHeight=dp(48);stateListAnimator=null;elevation=0f
                surface(this,if(id==AlertDialog.BUTTON_POSITIVE)green else Color.TRANSPARENT,if(id==AlertDialog.BUTTON_POSITIVE)Color.WHITE else green)
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
                surface(this,if(index==selected)sage else Color.TRANSPARENT)
                layoutParams=LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(4)}
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
        text=value;textSize=maxOf(14f,size);setTextColor(if(size<=14f)muted else ink);includeFontPadding=false;setPadding(0,0,0,0);setLineSpacing(dp(2).toFloat(),1f)
        typeface=Typeface.create("sans-serif",if(bold)Typeface.BOLD else Typeface.NORMAL);parent.addView(this,LinearLayout.LayoutParams(if(parent.orientation==LinearLayout.HORIZONTAL)-2 else -1,-2).apply{bottomMargin=dp(4)})
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
            addState(intArrayOf(android.R.attr.state_focused),shape(Color.WHITE,green,10))
            addState(intArrayOf(),shape(Color.WHITE,controlOutline,10))
        }
    }
    fun styleSwitch(control:Switch){
        // Conservar la geometría del control Android; sólo tematizar sus estados.
        control.showText=false;control.switchPadding=dp(16)
        control.trackTintList=ColorStateList(arrayOf(intArrayOf(android.R.attr.state_enabled,android.R.attr.state_checked),intArrayOf(android.R.attr.state_enabled),intArrayOf()),intArrayOf(green,Color.rgb(179,188,195),Color.rgb(218,224,228)))
        control.thumbTintList=ColorStateList(arrayOf(intArrayOf(android.R.attr.state_checked),intArrayOf()),intArrayOf(Color.WHITE,Color.rgb(91,109,121)))
    }
    fun button(parent:LinearLayout,title:String,action:()->Unit):Button=Button(activity).apply{
        text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL);surface(this,green,Color.WHITE);stateListAnimator=null;elevation=0f;minimumHeight=dp(48);setPadding(dp(14),dp(8),dp(14),dp(8))
        parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{topMargin=dp(8);bottomMargin=dp(3)})
        isEnabled=!isDemo();alpha=1f;setOnClickListener{if(!isBusy())action()}
        pressFeedback(this)
    }
    fun actionButton(parent:LinearLayout,title:String,allowed:Boolean,action:()->Unit):Button=button(parent,title,action).apply{isEnabled=isEnabled&&allowed;alpha=1f}
    fun secondary(parent:LinearLayout,title:String,action:()->Unit):Button=button(parent,title,action).apply{surface(this,Color.WHITE,ink)}
    fun space(parent:LinearLayout=root,height:Int=8){parent.addView(View(activity),LinearLayout.LayoutParams(1,dp(height)))}
    fun divider(parent:LinearLayout){parent.addView(View(activity).apply{setBackgroundColor(outline)},LinearLayout.LayoutParams(-1,dp(1)).apply{topMargin=dp(12);bottomMargin=dp(12)})}
    fun tertiary(parent:LinearLayout,title:String,action:()->Unit):Button=button(parent,title,action).apply{
        surface(this,Color.TRANSPARENT,ink);gravity=Gravity.START or Gravity.CENTER_VERTICAL
        layoutParams=LinearLayout.LayoutParams(-1,-2);setPadding(0,dp(8),0,dp(8))
    }
    fun rowAction(parent:LinearLayout,title:String,kind:String,action:()->Unit):Button=tertiary(parent,title,action).apply{
        setCompoundDrawablesWithIntrinsicBounds(AireIcon(activity,kind,muted,20),null,null,null);compoundDrawablePadding=dp(12)
    }
    fun sectionTitle(parent:LinearLayout,title:String,kind:String){
        val row=LinearLayout(activity).apply{gravity=Gravity.CENTER_VERTICAL};parent.addView(row)
        row.addView(ImageView(activity).apply{setImageDrawable(AireIcon(activity,kind,muted,21));importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO},LinearLayout.LayoutParams(dp(21),dp(21)).apply{marginEnd=dp(10)})
        text(row,title,18f,true)
    }
    fun iconAction(parent:LinearLayout,title:String,kind:String,action:()->Unit):ImageButton=ImageButton(activity).apply{
        contentDescription=title;setImageDrawable(AireIcon(activity,kind,green,22));background=RippleDrawable(ColorStateList.valueOf(sage),null,shape(Color.WHITE,radius=10));setPadding(dp(12),dp(12),dp(12),dp(12))
        parent.addView(this,LinearLayout.LayoutParams(dp(48),dp(48)));setOnClickListener{if(!isBusy())action()}
    }
    fun card(parent:LinearLayout=root,color:Int=Color.WHITE):LinearLayout=column().apply{
        background=shape(color,if(color==Color.WHITE)outline else Color.TRANSPARENT);setPadding(dp(16),dp(16),dp(16),dp(16));parent.addView(this,LinearLayout.LayoutParams(-1,-2).apply{bottomMargin=dp(12)})}
    fun badge(parent:LinearLayout,value:String,color:Int=neutralSurface,foreground:Int=muted):TextView=TextView(activity).apply{
        text=value;textSize=12f;typeface=Typeface.create("sans-serif-medium",0);setTextColor(foreground);background=shape(color,radius=6)
        setPadding(dp(9),dp(4),dp(9),dp(4));parent.addView(this,LinearLayout.LayoutParams(-2,-2).apply{marginEnd=dp(6);bottomMargin=dp(6)})
    }
    fun disclosure(parent:LinearLayout,title:String,key:String,content:(LinearLayout)->Unit){
        val wrapper=column();parent.addView(wrapper,LinearLayout.LayoutParams(-1,-2))
        val body=column();content(body)
        val header=FrameLayout(activity);wrapper.addView(header,LinearLayout.LayoutParams(-1,-2))
        val toggle=Button(activity).apply{
            text=title;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",0)
            minimumHeight=dp(48);stateListAnimator=null;elevation=0f;gravity=Gravity.START or Gravity.CENTER_VERTICAL
            setPadding(dp(12),dp(8),dp(44),dp(8));surface(this,Color.TRANSPARENT,ink);pressFeedback(this)
        }
        header.addView(toggle,FrameLayout.LayoutParams(-1,-2))
        val arrow=ImageView(activity).apply{setImageDrawable(AireIcon(activity,"chevron",muted,20));importantForAccessibility=View.IMPORTANT_FOR_ACCESSIBILITY_NO;isClickable=false}
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
            arrow.animate().rotation(if(expanded)180f else 0f).setDuration(200).start()
            body.alpha=if(expanded)0f else 1f;body.animate().alpha(if(expanded)1f else 0f).setDuration(180).start()
            val width=(wrapper.width.takeIf{it>0}?:activity.resources.displayMetrics.widthPixels-dp(64))
            body.measure(View.MeasureSpec.makeMeasureSpec(width,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
            val height=body.measuredHeight
            moving=true;body.visibility=View.VISIBLE
            ValueAnimator.ofInt(if(expanded)0 else height,if(expanded)height else 0).apply{
                duration=200;interpolator=DecelerateInterpolator()
                addUpdateListener{body.layoutParams=body.layoutParams.apply{this.height=it.animatedValue as Int}}
                addListener(object:android.animation.AnimatorListenerAdapter(){override fun onAnimationEnd(animation:android.animation.Animator){
                    body.layoutParams=body.layoutParams.apply{this.height=-2};body.visibility=if(expanded)View.VISIBLE else View.GONE;body.alpha=1f;moving=false
                }})
                start()
            }
        }
    }
}
