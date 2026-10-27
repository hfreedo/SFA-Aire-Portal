"""Recorrido visual de la APK en el AVD propio, sin cuentas ni envíos reales."""
import json,os,re,subprocess,time,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ADB=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/platform-tools/adb.exe'
OUT=ROOT/'artifacts/android-073';OUT.mkdir(exist_ok=True)
def adb(*args):return subprocess.check_output([str(ADB),'-s','emulator-5554',*args],stderr=subprocess.STDOUT,timeout=45)
def observe(name):
    adb('shell','uiautomator','dump','/sdcard/sfa-073-review.xml')
    raw=adb('shell','cat','/sdcard/sfa-073-review.xml');(OUT/(name+'.xml')).write_bytes(raw)
    (OUT/(name+'.png')).write_bytes(adb('exec-out','screencap','-p'))
    return ET.fromstring(raw)
def click(label,prefix=False):
    for attempt in range(6):
        tree=observe('control')
        nodes=[n for n in tree.iter('node') if n.get('clickable')=='true' and n.get('enabled')=='true' and any((v.startswith(label) if prefix else v==label) for v in [n.get('text',''),n.get('content-desc','')])]
        if nodes:
            assert len(nodes)==1,label
            x1,y1,x2,y2=map(int,re.findall(r'\d+',nodes[0].get('bounds')))
            if y2>y1 and x2>x1:
                adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2));time.sleep(.3);return
        adb('shell','input','swipe','360','1250','360','600','300')
    raise AssertionError('No se encontró el control: '+label)
def main():
    assert 'SFA_Aire_Visual_API30' in adb('emu','avd','name').decode()
    old=adb('shell','settings','get','system','font_scale').decode().strip()
    try:
        for profile,scale in [('normal','1.0'),('letra-130','1.3')]:
            adb('shell','settings','put','system','font_scale',scale)
            adb('shell','am','force-stop','org.sfa.aire')
            adb('shell','am','start','-W','-n','org.sfa.aire/.LauncherActivity');time.sleep(.7)
            observe(profile+'-acceso');click('Explorar demostración')
            tree=observe(profile+'-aula')
            assert any(n.get('text')=='SIMULACIÓN' for n in tree.iter('node'))
            assert not any(n.get('text')=='Aula seleccionada' for n in tree.iter('node'))
            click('Avisos');observe(profile+'-avisos')
            click('Detalles de entrega',prefix=True);observe(profile+'-entrega-expandida')
            click('Ajustes');observe(profile+'-ajustes')
            click('Detalles del registro',prefix=True);observe(profile+'-registro-expandido')
            click('Mi aula');observe(profile+'-regreso-aula')
        (OUT/'revision.json').write_text(json.dumps({'apk':'0.7.3','avd':'SFA_Aire_Visual_API30','profiles':['normal','font130'],'screens':['acceso','aula','avisos','ajustes','entrega','registro'],'cloud_auth':False,'real_fcm':False,'physical_a02':False},indent=2),encoding='utf-8')
        print('PASS: recorrido Android nativo normal y letra 130%, DEMO sin cuentas ni FCM')
    finally:
        if old=='null':adb('shell','settings','delete','system','font_scale')
        else:adb('shell','settings','put','system','font_scale',old)
if __name__=='__main__':main()
