"""Verifica el ZIP exacto extraído usando sólo sus ejecutables para arrancar servicios."""
import argparse,hashlib,json,os,socket,subprocess,time,uuid,zipfile
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def wait_health(base,proc,identity):
    for _ in range(160):
        try:
            h=httpx.get(base+'/health',timeout=.5).json()
            if h.get('workspace')==identity:return h
        except (httpx.HTTPError,ValueError):pass
        if proc.poll() is not None:raise RuntimeError('El ejecutable terminó antes de iniciar; revise el log de extracción.')
        time.sleep(.25)
    raise RuntimeError('El receptor portable no respondió')
def stop(base,root,data='data'):
    try:
        h=httpx.get(base+'/health',timeout=1).json();identity=hashlib.sha256(str(root).encode()).hexdigest()[:12]
        if h.get('workspace')!=identity:return
        key=(root/data/'clave_conexion.txt').read_text().strip()
        r=httpx.post(base+'/api/maintenance/shutdown',json={'instance_id':h['instance_id']},headers={'Authorization':'Bearer '+key},timeout=3);r.raise_for_status()
    except (httpx.HTTPError,OSError,ValueError,KeyError):pass
def kill_owned(proc):
    if proc.poll() is None:subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('archive',type=Path);parser.add_argument('--report',default='VALIDACION_PORTABLE_072.json');args=parser.parse_args()
    destination=ROOT/'artifacts'/('portable-clean-'+uuid.uuid4().hex[:8]);destination.mkdir()
    with zipfile.ZipFile(args.archive) as z:
        assert z.testzip() is None
        for name in z.namelist():assert (destination/name).resolve().is_relative_to(destination.resolve())
        z.extractall(destination)
    root=destination/'SFA_Aire';manifest=json.loads((root/'MANIFIESTO.json').read_text())
    for name,digest in manifest['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    assert not (root/'data').exists() and not (root/'secrets').exists() and not (root/'.venv').exists()
    env=os.environ.copy();env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
    for key in ['PYTHONPATH','PYTHONHOME','VIRTUAL_ENV']:env.pop(key,None)
    canary=destination/'unrelated-installation';canary.mkdir();(canary/'keep.txt').write_text('unchanged')
    env.update(SFA_DATA_DIR=str(canary),SFA_CLOUD_CONFIG=str(canary/'private.json'),SFA_PUBLIC_CONFIG=str(canary/'private-public.json'),GOOGLE_APPLICATION_CREDENTIALS=str(canary/'account.json'),SFA_API_TOKEN='never-use-this-inherited-token')
    identity=hashlib.sha256(str(root).encode()).hexdigest()[:12];port=free_port();base=f'http://127.0.0.1:{port}'
    log=(destination/'worker.log').open('w',encoding='utf-8');proc=subprocess.Popen([str(root/'SFA_Aire_Receptor.exe'),'receiver','--no-browser','--port',str(port)],cwd=root,env=env,stdout=log,stderr=log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        wait_health(base,proc,identity)
        public=httpx.get(base+'/api/public-config').json();assert public['configured'] is True and public['url']=='https://taynrhyoxmweqnxlnqfj.supabase.co'
        assert httpx.get(base+'/remoto').status_code==200 and httpx.get(base+'/invitacion').status_code==200
        assert httpx.get(base+'/api/state').status_code==401
        key=(root/'data/clave_conexion.txt').read_text().strip();assert key!=env['SFA_API_TOKEN'];headers={'Authorization':'Bearer '+key}
        state=httpx.get(base+'/api/state',headers=headers).json();assert state['source']=='detenido' and state['incidents']==[] and state['devices']==[]
        assert httpx.get(base+'/api/ports',headers=headers).status_code==200
        assert httpx.post(base+'/api/simulation',headers=headers,json={'scenario':'normal'}).status_code==200
        for _ in range(30):
            if httpx.get(base+'/api/state',headers=headers).json().get('latest'):break
            time.sleep(.25)
        else:raise AssertionError('Simulador portable sin muestras')
        httpx.post(base+'/api/stop',headers=headers).raise_for_status()
        duplicate=subprocess.run([str(root/'SFA_Aire_Receptor.exe'),'receiver','--no-browser','--port',str(port)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
        assert duplicate.returncode==0 and 'ya est' in duplicate.stdout
    finally:
        stop(base,root)
        try:proc.wait(timeout=12)
        except subprocess.TimeoutExpired:kill_owned(proc)
        log.close()
    # Ejecutable del panel: inicia cloud y demo con el worker incluido, sin .venv.
    panel=subprocess.Popen([str(root/'Panel SFA Aire.exe'),'--self-check'],cwd=root,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        assert panel.wait(timeout=60)==0
        report=json.loads((root/'artifacts/panel-self-check.json').read_text());assert report['executable'] and report['isolated_demo_without_cloud'] and report['tk_assets_verified']
    finally:
        kill_owned(panel)
        ports=json.loads((root/'data/panel/runtime-ports.json').read_text())
        for name,p in ports.items():stop(f'http://127.0.0.1:{p}',root,'artifacts/panel-demo' if name=='demo' else 'data')
    # La descarga temporal sólo sirve la APK y no publica directorios locales.
    wifi_port=free_port();wifi_log=(destination/'wifi.log').open('w',encoding='utf-8')
    wifi=subprocess.Popen([str(root/'SFA_Aire_Receptor.exe'),'apk-wifi','--host','127.0.0.1','--port',str(wifi_port)],cwd=root,env=env,stdout=wifi_log,stderr=wifi_log,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    try:
        for _ in range(120):
            try:
                meta=json.loads((root/'data/apk-wifi.json').read_text());r=httpx.get(meta['url'],timeout=.5)
                if r.status_code==200:break
            except (OSError,ValueError,httpx.HTTPError):pass
            if wifi.poll() is not None:raise RuntimeError('No arrancó la descarga APK portable')
            time.sleep(.25)
        else:raise RuntimeError('Sin descarga APK')
        assert hashlib.sha256(httpx.get(meta['url']+'/apk').content).hexdigest()==meta['sha256']
        assert httpx.get(f'http://127.0.0.1:{wifi_port}/data').status_code==404
    finally:kill_owned(wifi);wifi_log.close()
    assert list(canary.iterdir())==[canary/'keep.txt'] and (canary/'keep.txt').read_text()=='unchanged'
    result={'version':manifest['version'],'archive_sha256':hashlib.sha256(args.archive.read_bytes()).hexdigest(),'zip_and_manifest':'passed','private_directories_absent_initially':True,'standalone_worker_and_panel':'passed','tk_logo_and_qr':'passed','python_and_node_absent_from_path':True,'receiver_ui_ports_simulation_shutdown':'passed','duplicate_instance_guard':'passed','demo_without_cloud':'passed','apk_wifi_private_path':'passed','inherited_private_environment_ignored':True,'cloud_or_real_fcm_test_during_portable_check':False,'physical_hardware_test':False,'tested_os':'Windows 11 x64'}
    target=ROOT/'Entregas'/args.report;target.write_text(json.dumps(result,indent=2),encoding='utf-8');print('PASS: ZIP limpio, runtime autónomo, panel, demo, COM, simulación, detención, duplicados, APK por Wi-Fi y aislamiento. Sin FCM real.')
if __name__=='__main__':main()
