package org.sfa.aire.ui

import android.content.Context
import android.graphics.*
import android.graphics.drawable.Drawable

/** Iconos vectoriales propios de la interfaz; no representan controles del hardware. */
class AireIcon(context:Context,private val kind:String,color:Int,size:Int=26):Drawable(){
 private val pixels=(size*context.resources.displayMetrics.density).toInt()
 private val pen=Paint(Paint.ANTI_ALIAS_FLAG).apply{this.color=color;style=Paint.Style.STROKE;strokeWidth=1.7f;strokeCap=Paint.Cap.ROUND;strokeJoin=Paint.Join.ROUND}
 override fun getIntrinsicWidth()=pixels
 override fun getIntrinsicHeight()=pixels
 override fun setAlpha(alpha:Int){pen.alpha=alpha}
 override fun setColorFilter(filter:ColorFilter?){pen.colorFilter=filter}
 @Deprecated("Drawable opacity") override fun getOpacity()=PixelFormat.TRANSLUCENT
 override fun draw(canvas:Canvas){
  canvas.save();canvas.translate(bounds.left.toFloat(),bounds.top.toFloat());canvas.scale(bounds.width()/24f,bounds.height()/24f)
  fun path(vararg points:Float){val p=Path();p.moveTo(points[0],points[1]);for(i in 2 until points.size step 2)p.lineTo(points[i],points[i+1]);canvas.drawPath(p,pen)}
  when(kind){
   "chevron"->path(7f,9f,12f,14f,17f,9f)
   "check"->path(6f,12f,10f,16f,18f,8f)
   "temperature"->{val p=Path();p.moveTo(9f,14f);p.lineTo(9f,5f);p.cubicTo(9f,1f,15f,1f,15f,5f);p.lineTo(15f,14f);p.cubicTo(21f,20f,8f,25f,7f,18f);p.cubicTo(6.8f,16f,8f,14.5f,9f,14f);canvas.drawPath(p,pen);path(12f,8f,12f,17f);canvas.drawCircle(12f,18f,1.4f,pen);path(18f,6f,21f,6f);path(18f,10f,20f,10f)}
   "humidity"->{val p=Path();p.moveTo(12f,2.5f);p.cubicTo(9f,7f,5f,11f,5f,15f);p.cubicTo(5f,24f,19f,24f,19f,15f);p.cubicTo(19f,11f,15f,7f,12f,2.5f);canvas.drawPath(p,pen);canvas.drawArc(8f,12f,16f,20f,75f,90f,false,pen)}
   "air"->{path(3f,8f,15f,8f);canvas.drawArc(13f,3f,19f,9f,-150f,250f,false,pen);path(3f,12f,20f,12f);path(3f,16f,13f,16f);canvas.drawArc(11f,15f,17f,21f,-100f,260f,false,pen)}
   "home"->{path(3f,11f,12f,3f,21f,11f);path(5f,10f,5f,21f,19f,21f,19f,10f);path(10f,21f,10f,15f,14f,15f,14f,21f)}
   "bell"->{val p=Path();p.moveTo(5f,17f);p.lineTo(7f,14f);p.lineTo(7f,9f);p.cubicTo(7f,2f,17f,2f,17f,9f);p.lineTo(17f,14f);p.lineTo(19f,17f);p.close();canvas.drawPath(p,pen);canvas.drawArc(9f,17f,15f,23f,20f,140f,false,pen)}
   "account"->{canvas.drawCircle(12f,7f,3.5f,pen);canvas.drawArc(4f,12f,20f,25f,185f,170f,false,pen)}
   "share"->{canvas.drawCircle(6f,12f,2.5f,pen);canvas.drawCircle(18f,5f,2.5f,pen);canvas.drawCircle(18f,19f,2.5f,pen);path(8f,11f,16f,6f);path(8f,13f,16f,18f)}
   "note"->{path(14f,3f,4f,3f,4f,21f,20f,21f,20f,11f);path(10f,14f,11f,10f,18f,3f,21f,6f,14f,13f,10f,14f)}
   "refresh"->{canvas.drawArc(4f,4f,20f,20f,45f,290f,false,pen);path(20f,4f,20f,10f,14f,10f)}
   "logout"->{path(10f,3f,4f,3f,4f,21f,10f,21f);path(10f,12f,21f,12f);path(17f,8f,21f,12f,17f,16f)}
   "settings"->{for((y,x) in listOf(6f to 9f,12f to 16f,18f to 7f)){path(3f,y,x-3f,y);path(x+3f,y,21f,y);canvas.drawCircle(x,y,2.4f,pen)}}
   else->{canvas.drawCircle(12f,12f,9f,pen);path(12f,11f,12f,17f);canvas.drawPoint(12f,7f,pen)}
  }
  canvas.restore()
 }
}
