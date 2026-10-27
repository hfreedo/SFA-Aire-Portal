"""Portable por lista permitida; no recorre ni copia datos de la instalación."""
import base64,hashlib,importlib.metadata,io,json,re,shutil,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];VERSION='0.7.3'
sys.path.insert(0,str(ROOT))
STAGE=ROOT/'artifacts/portable-stage/SFA_Aire';OUT=ROOT/'Entregas';ARCHIVE=OUT/f'SFA_Aire_Windows_{VERSION}_portable_x64.zip'

def forbidden_values():
    values={str(ROOT).encode(),str(Path.home()).encode()}
    def visit(data):
        if isinstance(data,dict):
            for k,v in data.items():
                if isinstance(v,str) and ((len(v)>=24 and re.search('secret|password|private_key|access_token|refresh_token',k,re.I)) or (k=='email' and '@' in v)):
                    values.add(v.encode());values.add(json.dumps(v)[1:-1].encode())
                    if 'PRIVATE KEY' in v:values.update(line.encode() for line in v.splitlines() if len(line)>40 and not line.startswith('---'))
                visit(v)
        elif isinstance(data,list):
            for item in data:visit(item)
    for file in (ROOT/'secrets').rglob('*.json'):
        try:visit(json.loads(file.read_text(encoding='utf-8-sig')))
        except (ValueError,OSError):pass
    return values

def audit(data,label,private):
    assert not any(v in data for v in private),'Valor privado encontrado: '+label
    assert not re.search(rb'sb_secret_[A-Za-z0-9_-]{15,}',data),'Clave privilegiada: '+label
    assert not re.search(rb'-----BEGIN PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]{100,}',data.replace(b'\\n',b'\n')),'PEM privado: '+label
    for raw in re.findall(rb'eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}',data):
        c=raw.split(b'.')[1]
        claims=json.loads(base64.urlsafe_b64decode(c+b'='*(-len(c)%4)));assert claims.get('role')=='anon','JWT privado: '+label

def main():
    assert STAGE.resolve().is_relative_to((ROOT/'artifacts').resolve()) and STAGE.name=='SFA_Aire'
    if STAGE.exists():shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True);OUT.mkdir(exist_ok=True)
    def copy(source,target=None):
        src=ROOT/source;dest=STAGE/(target or source);assert src.is_file(),source;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    copy('artifacts/portable-bin/Panel SFA Aire.exe','Panel SFA Aire.exe');copy('artifacts/portable-bin/SFA_Aire_Receptor.exe','SFA_Aire_Receptor.exe')
    for name in ['iniciar.py','LICENCIA_DE_USO_RESTRINGIDO.md','AUTORIA.md','docs/GUIA_USO.html','docs/GUIA_PUBLICA.md','docs/capturas/panel-ejemplo.png','herramientas/compartir_apk_wifi.py','herramientas/apk_release.py']:
        copy(name)
    copy('docs/README_PUBLICO.md','README.md')
    for folder in ['servidor_pc','arduino']:
        for p in (ROOT/folder).rglob('*'):
            if p.is_file() and p.suffix in {'.py','.ino','.txt'} and '__pycache__' not in p.parts:copy(p.relative_to(ROOT))
    for p in (ROOT/'interfaz_web/dist').rglob('*'):
        if p.is_file():copy(p.relative_to(ROOT))
    copy('Branding/logo/sfa-aire-verde-transparente.png')
    copy('Branding/logo/sfa-aire.ico')
    metadata=OUT/'ANDROID_ACTUAL.json'
    if not metadata.is_file():metadata=ROOT/'docs/ANDROID_PILOTO_072.json'
    release=json.loads(metadata.read_text());assert release['version']=='0.7.2'
    assert hashlib.sha256((OUT/release['file']).read_bytes()).hexdigest()==release['sha256']
    copy('Entregas/'+release['file']);copy(metadata.relative_to(ROOT),'Entregas/ANDROID_ACTUAL.json')
    public_path=ROOT/'secrets/supabase-public.json'
    if not public_path.is_file():public_path=ROOT/'config/public-config.json'
    public=json.loads(public_path.read_text(encoding='utf-8-sig'))
    from servidor_pc.cloud import PublicConnection
    cfg=PublicConnection(url=public['url'],publishable_key=public.get('publishable_key') or public['key'])
    (STAGE/'config').mkdir();(STAGE/'config/public-config.json').write_text(cfg.model_dump_json(indent=2),encoding='utf-8')
    dependencies=[]
    for dist in importlib.metadata.distributions():
        name=dist.metadata['Name'];dependencies.append({'name':name,'version':dist.version})
        for f in dist.files or []:
            if any(tag in f.name.lower() for tag in ('license','licence','copying','notice')) and '.dist-info' in str(f) and dist.locate_file(f).is_file():
                dest=STAGE/'licenses'/re.sub('[^a-zA-Z0-9_.-]','_',name)/Path(*f.parts[1:]);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(dist.locate_file(f),dest)
    for name,source in [('Python.txt',Path(sys.base_prefix)/'LICENSE.txt'),('Tcl.txt',ROOT/'docs/licenses/Tcl.txt'),('Tk.txt',Path(sys.base_prefix)/'tcl/tk8.6/license.terms')]:
        assert source.is_file(),source;dest=STAGE/'licenses'/name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
    for p in (ROOT/'interfaz_web/node_modules').rglob('*'):
        if p.is_file() and p.name.lower() in {'license','license.txt','license.md','licence','copying','notice','notice.txt'}:
            dest=STAGE/'licenses/web'/p.relative_to(ROOT/'interfaz_web/node_modules');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    (STAGE/'licenses/dependencies.json').write_text(json.dumps(dependencies,indent=2),encoding='utf-8')
    (STAGE/'THIRD_PARTY_NOTICES.md').write_text('''# Componentes de terceros

Python (PSF), Tcl/Tk (licencias propias), PyInstaller (GPL con excepción de bootloader),
FastAPI y Pydantic (MIT), Uvicorn y PySerial (BSD), Firebase Admin y sus dependencias
(incluyendo Apache 2.0) conservan sus licencias. Se incluyen los avisos del runtime
en licenses/; dependencies.json registra las versiones del entorno de construcción.

La interfaz construida utiliza React (MIT), Vite (MIT), TypeScript (Apache 2.0),
Lucide (ISC), Supabase JS (MIT) y qrcode (MIT). La APK usa Kotlin, Android y Firebase;
sus componentes conservan las licencias y avisos de sus distribuidores.
Estas licencias son independientes de las restricciones sobre el código propio.
''',encoding='utf-8')
    private=forbidden_values();files={}
    for p in STAGE.rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(STAGE).as_posix();assert rel.split('/')[0] not in {'data','secrets','artifacts','.venv'}
        raw=p.read_bytes();audit(raw,rel,private);files[rel]=hashlib.sha256(raw).hexdigest()
        if p.suffix=='.exe':
            from PyInstaller.archive.readers import CArchiveReader
            archive=CArchiveReader(str(p))
            for name,item in archive.toc.items():
                if item[-1]=='z':
                    pyz=archive.open_embedded_archive(name)
                    for module in pyz.toc:
                        data=pyz.extract(module,raw=True)
                        if data:audit(data,rel+'/'+module,private)
                elif item[-1] in {'s','m','x','b'}:
                    data=archive.extract(name)
                    if data:
                        audit(data,rel+'/'+name,private)
                        if name.endswith('.zip') and zipfile.is_zipfile(io.BytesIO(data)):
                            with zipfile.ZipFile(io.BytesIO(data)) as nested:
                                for entry in nested.namelist():audit(nested.read(entry),rel+'/'+name+'/'+entry,private)
        if p.suffix=='.apk':
            with zipfile.ZipFile(p) as z:
                assert z.testzip() is None
                for n in z.namelist():
                    assert n.split('/')[-1] not in {'firebase-admin.json','firebase-cloud-account.json','admin-auth-session.json','supabase-pc.json'}
                    audit(z.read(n),'APK/'+n,private)
    manifest={'version':VERSION,'platform':'Windows x64','contains_external_python_runtime':False,'contains_private_data':False,'files':files}
    (STAGE/'MANIFIESTO.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    with zipfile.ZipFile(ARCHIVE,'w',zipfile.ZIP_DEFLATED) as z:
        for p in STAGE.rglob('*'):
            if p.is_file():z.write(p,'SFA_Aire/'+p.relative_to(STAGE).as_posix())
    with zipfile.ZipFile(ARCHIVE) as z:assert z.testzip() is None
    print(f'Portable preparado: {ARCHIVE.name}; {len(files)} archivos; sin sesiones, bases ni credenciales privadas.')

if __name__=='__main__':main()
