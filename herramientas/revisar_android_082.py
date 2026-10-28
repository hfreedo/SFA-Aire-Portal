"""Recorrido nativo 0.8.2: bandeja, archivo personal y sensores. Sin cloud."""
import json,time,re
import revisar_android_073 as r
if __name__=='__main__':
 assert 'versionName=0.8.2' in r.adb('shell','dumpsys','package','org.sfa.aire').decode()
 assert 'SFA_Aire_Visual_API30' in r.adb('emu','avd','name').decode()
 r.OUT=r.ROOT/'artifacts/android-082';r.OUT.mkdir(exist_ok=True)
 old=r.adb('shell','settings','get','system','font_scale').decode().strip()
 try:
  for profile,scale in [('normal','1.0'),('letra-130','1.3')]:
   r.adb('shell','settings','put','system','font_scale',scale)
   r.adb('shell','am','force-stop','org.sfa.aire');r.adb('shell','am','start','-W','-n','org.sfa.aire/.LauncherActivity');time.sleep(.7)
   r.observe(profile+'-acceso');r.click('Explorar demostración');r.observe(profile+'-aula')
   r.click('Avisos');tree=r.observe(profile+'-avisos-replegados')
   assert not any(n.get('text')=='Datos simulados del aviso' for n in tree.iter('node'))
   r.click('Detalles y acciones');tree=r.observe(profile+'-aviso-expandido')
   assert any(n.get('text')=='560 ADC' for n in tree.iter('node'))
   r.click('Archivar en este teléfono');r.observe(profile+'-pendientes-archivado')
   if(scale=='1.3'):
    tree=r.observe(profile+'-categorias');node=next(n for n in tree.iter('node') if n.get('class')=='android.widget.HorizontalScrollView');x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')));r.adb('shell','input','swipe',str(x2-12),str((y1+y2)//2),str(x1+12),str((y1+y2)//2),'250')
   r.click('Archivo, 1 avisos',prefix=True);r.observe(profile+'-archivo-personal')
   r.click('Restaurar en la bandeja');r.observe(profile+'-archivo-restaurado')
   if(scale=='1.3'):
    tree=r.observe(profile+'-categorias-retorno');node=next(n for n in tree.iter('node') if n.get('class')=='android.widget.HorizontalScrollView');x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')));r.adb('shell','input','swipe',str(x1+12),str((y1+y2)//2),str(x2-12),str((y1+y2)//2),'250')
   r.click('Pendientes, 1 avisos',prefix=True);r.observe(profile+'-pendiente-restaurado')
   r.click('Ajustes');r.observe(profile+'-ajustes')
  (r.OUT/'revision.json').write_text(json.dumps({'apk':'0.8.2','avd':'SFA_Aire_Visual_API30','profiles':['normal','font130'],'collapsed':True,'archive_restore':True,'cloud_auth':False,'real_fcm':False,'physical_a02':False},indent=2),encoding='utf-8')
  print('PASS: Android normal/130%, collapsed -> evidence -> personal archive -> restore, no cloud')
 finally:
  r.adb('shell','settings','delete','system','font_scale') if old=='null' else r.adb('shell','settings','put','system','font_scale',old)
