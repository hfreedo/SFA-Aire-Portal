"""Exportación por lista permitida: nunca copia el directorio de trabajo completo."""
import hashlib,json,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'publication/repository';out.mkdir(parents=True,exist_ok=True)
files=[]
for directory in ['interfaz_web/src','supabase/migrations','supabase/functions','servidor_pc','arduino','tests','android_app/app/src']:
    files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css','.png','.sql','.json','.py','.ino','.txt','.kt','.xml'} and p.name not in {'sfa-public.json','google-services.json'})
for name in ['interfaz_web/package.json','interfaz_web/package-lock.json','interfaz_web/tsconfig.json','interfaz_web/vite.config.ts','interfaz_web/index.html','interfaz_web/remoto.html','interfaz_web/portal.html','interfaz_web/.env.hosting','firebase.json','.firebaserc','supabase/config.toml','herramientas/preparar_portal_publico.py','herramientas/publicar_firebase_hosting.py','herramientas/preparar_repositorio_portal.py','docs/PORTAL_PUBLICO_E_INVITACIONES.md','docs/README_PUBLICO.md','docs/capturas/panel-ejemplo.png','docs/GUIA_PUBLICA.md','docs/ANDROID_PILOTO_072.json','docs/GUIA_USO.html','docs/licenses/Tcl.txt','LICENCIA_DE_USO_RESTRINGIDO.md','AUTORIA.md','iniciar.py','panel_inicio.py','herramientas/portable_worker.py','herramientas/compilar_portable.ps1','herramientas/empaquetar_portable.py','herramientas/verificar_portable.py','herramientas/requirements-panel.txt','herramientas/empaquetar.py','herramientas/cambiar_clave_admin.py','android_app/build.gradle.kts','android_app/app/build.gradle.kts','android_app/settings.gradle.kts','android_app/gradle.properties','android_app/gradlew','android_app/gradlew.bat','android_app/gradle/wrapper/gradle-wrapper.properties','android_app/gradle/wrapper/gradle-wrapper.jar','herramientas/compartir_apk_wifi.py','herramientas/apk_release.py','herramientas/qr_wifi.py','herramientas/sql-check/first-pc.test.mjs','herramientas/sql-check/package.json','herramientas/sql-check/package-lock.json','herramientas/sql-check/cloud-fixture.mjs','herramientas/sql-check/invitations.test.mjs','herramientas/sql-check/invitations-edge.test.mjs']:
    files.append(ROOT/name)
manifest=[]
for file in files:
    assert file.is_file(),file
    relative=file.relative_to(ROOT);raw=file.read_bytes()
    assert not re.search(rb'-----BEGIN PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]{100,}',raw.replace(b'\\n',b'\n')),relative
    assert relative.parts[0] not in {'secrets','data','Entregas','artifacts'} and not any(part in {'node_modules','.git'} for part in relative.parts)
    target=out/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    manifest.append({'path':relative.as_posix(),'sha256':hashlib.sha256(raw).hexdigest()})
(out/'.gitignore').write_text('node_modules/\n.venv/\n/secrets/\n/data/\n/artifacts/\n.firebase/\ninterfaz_web/dist/\ninterfaz_web/dist-hosting/\n/publication/\n.env\n*.log\n',encoding='utf-8')
(out/'README.md').write_text((ROOT/'docs/README_PUBLICO.md').read_text(encoding='utf-8'),encoding='utf-8')
(out/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Exportación de código preparada:',len(files),'archivos fuente; sin datos ni credenciales.')
