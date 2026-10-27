"""Despliegue estático con la API oficial. No modifica IAM, APIs habilitadas ni Billing.

Alternativa al CLI cuando su comprobación de Service Usage exige permisos adicionales.
https://firebase.google.com/docs/hosting/api-deploy
"""
import gzip,hashlib,json,argparse
from pathlib import Path
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--resume-created',action='store_true');args=parser.parse_args()
account=ROOT/'secrets/firebase-cloud-account.json'
assert json.loads(account.read_text())['project_id']=='sfa-aire-aulas'
session=AuthorizedSession(service_account.Credentials.from_service_account_file(str(account),scopes=['https://www.googleapis.com/auth/firebase.hosting']))
api='https://firebasehosting.googleapis.com/v1beta1/'
def call(method,url,**kwargs):
    r=session.request(method,url,timeout=40,**kwargs)
    if not r.ok:raise RuntimeError(f'Hosting: HTTP {r.status_code}: '+r.json().get('error',{}).get('message','Solicitud rechazada'))
    return r.json() if r.content else {}
hosting=json.loads((ROOT/'firebase.json').read_text())['hosting']
config={'rewrites':[{'glob':'**','path':'/index.html'}], 'headers':[{'glob':entry['source'],'headers':{h['key']:h['value'] for h in entry['headers']}} for entry in hosting['headers']]}
folder=ROOT/hosting['public'];files={};content={}
for file in folder.rglob('*'):
    if file.is_file():
        raw=file.read_bytes();assert b'BEGIN PRIVATE KEY' not in raw and b'firebase-adminsdk-' not in raw
        compressed=gzip.compress(raw,mtime=0);digest=hashlib.sha256(compressed).hexdigest()
        files['/'+file.relative_to(folder).as_posix()]=digest;content[digest]=compressed
assert '/index.html' in files and '/public-config.json' in files and len(files)<=50
assert sum(map(len,content.values()))<5_000_000
state=ROOT/'artifacts/hosting-version.json';state.parent.mkdir(exist_ok=True)
if args.resume_created:
    version=json.loads(state.read_text())['name'];call('PATCH',api+version,params={'update_mask':'config'},json={'config':config})
else:
    created=call('POST',api+'sites/sfa-aire-aulas/versions',json={'config':config});version=created['name'];state.write_text(json.dumps(created),encoding='utf-8')
populate=call('POST',api+version+':populateFiles',json={'files':files})
upload=populate.get('uploadUrl','');assert upload.startswith('https://upload-firebasehosting.googleapis.com/upload/sites/sfa-aire-aulas/')
for i,digest in enumerate(populate.get('uploadRequiredHashes',[])):
    call('POST',upload+'/'+digest,data=content[digest],headers={'Content-Type':'application/octet-stream'})
    print('Archivo estático cargado',i+1,flush=True)
finalized=call('PATCH',api+version,params={'update_mask':'status'},json={'status':'FINALIZED'});assert finalized['status']=='FINALIZED'
release=call('POST',api+'sites/sfa-aire-aulas/releases',params={'versionName':version})
evidence={'url':'https://sfa-aire-aulas.web.app','version':version,'release':release['name'],'files':len(files),'gzip_bytes':sum(map(len,content.values())),'billing_modified':False,'iam_modified':False}
(ROOT/'artifacts/hosting-release.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
print(json.dumps(evidence))
