"""Reutiliza el recorrido nativo DEMO sobre la APK 0.7.4 instalada en el AVD propio."""
import json
import revisar_android_073 as review
if __name__=='__main__':
    assert 'versionName=0.7.4' in review.adb('shell','dumpsys','package','org.sfa.aire').decode()
    review.OUT=review.ROOT/'artifacts/android-074';review.OUT.mkdir(exist_ok=True)
    review.main()
    path=review.OUT/'revision.json';result=json.loads(path.read_text());result['apk']='0.7.4'
    path.write_text(json.dumps(result,indent=2),encoding='utf-8')
