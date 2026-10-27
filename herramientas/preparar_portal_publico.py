"""Copia exclusivamente el build web y la conexión pública validada. Sin secretos backend."""
import json,shutil,base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'interfaz_web/dist-hosting';target=ROOT/'publication/hosting'
config=json.loads((ROOT/'secrets/supabase-public.json').read_text(encoding='utf-8-sig'))
url=config.get('url') or config.get('supabase_url');key=config.get('key') or config.get('publishable_key')
assert url=='https://taynrhyoxmweqnxlnqfj.supabase.co'
assert key and not key.startswith('sb_secret_')
if key.startswith('eyJ'):
    claim=key.split('.')[1];assert json.loads(base64.urlsafe_b64decode(claim+'='*(-len(claim)%4)))['role']=='anon'
else:assert key.startswith('sb_publishable_')
assert (source/'portal.html').is_file()
assert target.resolve().is_relative_to(ROOT.resolve()) and target.name=='hosting'
if target.exists():shutil.rmtree(target)
target.mkdir(parents=True,exist_ok=True)
shutil.copytree(source,target,dirs_exist_ok=True)
shutil.copyfile(source/'portal.html',target/'index.html')
(target/'public-config.json').write_text(json.dumps({'configured':True,'url':url,'key':key}),encoding='utf-8')
assert sum(p.stat().st_size for p in target.rglob('*') if p.is_file())<5_000_000,'Build excede guarda de 5 MB'
for p in target.rglob('*'):
    if p.is_file():
        content=p.read_bytes()
        assert b'BEGIN PRIVATE KEY' not in content and b'"service_role"' not in content and b'firebase-adminsdk-' not in content
print('Portal público preparado: solo estáticos y clave pública; tamaño menor a 5 MB.')
