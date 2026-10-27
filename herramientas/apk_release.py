"""Manifiesto público de la APK distribuida; nunca contiene configuración privada."""
import hashlib,json,re
from pathlib import Path

def load_release(root):
    directory=(Path(root)/'Entregas').resolve()
    manifest=directory/'ANDROID_ACTUAL.json'
    release=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {
        'file':'SFA_Aire_0.6.2_firebase_configurado.apk','version':'0.6.2',
        'sha256':'2368a3789301e33f150042059fefe6e0a6072eec797ba22e5fdc4a704fc11924'}
    name=release.get('file','');version=release.get('version','');digest=release.get('sha256','')
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+\.apk',name):
        raise ValueError('Nombre de APK no válido')
    target=(directory/name).resolve()
    if target.parent!=directory or not re.fullmatch(r'\d+\.\d+\.\d+',version) or not re.fullmatch(r'[0-9a-f]{64}',digest):
        raise ValueError('Manifiesto Android no válido')
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
        raise ValueError('La APK no coincide con el manifiesto. Vuelva a preparar la entrega.')
    return {**release,'path':target}
