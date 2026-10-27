"""Grabación nativa a velocidad real, sólo en el AVD propio y modo DEMO."""
import json,re,subprocess,time
import revisar_android_073 as review

def main():
    assert 'SFA_Aire_Visual_API30' in review.adb('emu','avd','name').decode()
    assert 'versionName=0.7.4' in review.adb('shell','dumpsys','package','org.sfa.aire').decode()
    review.OUT=review.ROOT/'artifacts/android-074';review.OUT.mkdir(exist_ok=True)
    review.adb('shell','am','force-stop','org.sfa.aire')
    review.adb('shell','am','start','-W','-n','org.sfa.aire/.LauncherActivity')
    review.click('Explorar demostración');time.sleep(.5)
    tree=review.observe('grabacion-inicio')
    points={}
    for title in ['Mi aula','Avisos','Ajustes']:
        nodes=[n for n in tree.iter('node') if n.get('content-desc')==title and n.get('clickable')=='true']
        assert len(nodes)==1
        x1,y1,x2,y2=map(int,re.findall(r'\d+',nodes[0].get('bounds')))
        points[title]=str((x1+x2)//2),str((y1+y2)//2)
    remote='/sdcard/sfa-074-DEMO.mp4'
    process=subprocess.Popen([str(review.ADB),'-s','emulator-5554','shell','screenrecord','--time-limit','12','--bit-rate','2000000',remote],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    time.sleep(1)
    for title in ['Avisos','Ajustes','Mi aula','Ajustes','Avisos','Mi aula']:
        review.adb('shell','input','tap',*points[title]);time.sleep(1.1)
    stdout,stderr=process.communicate(timeout=18)
    assert process.returncode==0,(stdout+stderr).decode(errors='replace')
    payload=review.adb('exec-out','cat',remote);assert b'ftyp' in payload[:64]
    target=review.OUT/'SFA_Aire_0.7.4_movimiento_DEMO.mp4';target.write_bytes(payload)
    (review.OUT/'grabacion.json').write_text(json.dumps({'apk':'0.7.4','source':'native emulator screenrecord','duration_seconds':12,'playback_speed':'original','cloud_calls':False,'physical_phone':False,'file':target.name},indent=2),encoding='utf-8')
    print('Grabación nativa DEMO guardada; velocidad original, sin datos ni envíos reales')

if __name__=='__main__':main()
