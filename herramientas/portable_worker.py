"""Entrada congelada: sólo receptor y descarga temporal; nunca ejecuta rutas elegidas por red."""
import os
from pathlib import Path
import runpy
import sys

def main():
    root=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[1]
    if len(sys.argv)<2 or sys.argv[1] not in ('receiver','apk-wifi'):raise SystemExit('Componente portable no disponible')
    mode=sys.argv[1];args=sys.argv[2:]
    # Cada extracción crea su identidad y sus archivos privados. No hereda destinos
    # de datos/credenciales configurados para otra instalación en esta computadora.
    os.environ['GOOGLE_APPLICATION_CREDENTIALS']=''
    os.environ.pop('SFA_API_TOKEN',None)
    allowed_data=(root/'artifacts/panel-demo').resolve()
    demo=Path(os.environ.get('SFA_DATA_DIR',root/'data')).resolve()==allowed_data
    os.environ['SFA_DATA_DIR']=str(allowed_data if demo else root/'data')
    os.environ['SFA_CLOUD_CONFIG']=str(root/'artifacts/panel-demo-sin-cloud.json' if demo else root/'secrets/supabase-pc.json')
    os.environ['SFA_PUBLIC_CONFIG']=str(root/'artifacts/panel-demo-sin-cloud.json' if demo else root/'config/public-config.json')
    if mode=='receiver':
        import servidor_pc.main as service
        service.ROOT=root
        script=root/'iniciar.py'
    else:
        sys.path.insert(0,str(root/'herramientas'))
        script=root/'herramientas/compartir_apk_wifi.py'
    sys.argv=[str(script),*args]
    runpy.run_path(str(script),run_name='__main__')

if __name__=='__main__':main()
