"""Exportación por lista permitida: nunca copia el directorio de trabajo completo."""
import hashlib,json,shutil,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'publication/repository';out.mkdir(parents=True,exist_ok=True)
files=[]
for directory in ['interfaz_web/src','supabase/migrations','supabase/functions']:
    files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.ts','.tsx','.css','.png','.sql','.json'})
for name in ['interfaz_web/package.json','interfaz_web/package-lock.json','interfaz_web/tsconfig.json','interfaz_web/vite.config.ts','interfaz_web/index.html','interfaz_web/remoto.html','interfaz_web/portal.html','interfaz_web/.env.hosting','firebase.json','.firebaserc','supabase/config.toml','herramientas/preparar_portal_publico.py','herramientas/publicar_firebase_hosting.py','herramientas/preparar_repositorio_portal.py','docs/PORTAL_PUBLICO_E_INVITACIONES.md','herramientas/sql-check/package.json','herramientas/sql-check/package-lock.json','herramientas/sql-check/cloud-fixture.mjs','herramientas/sql-check/invitations.test.mjs','herramientas/sql-check/invitations-edge.test.mjs']:
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
(out/'README.md').write_text('''# SFA Aire · Portal de aulas

Portal: https://sfa-aire-aulas.web.app/remoto

Código del portal React y backend Supabase del proyecto educativo independiente SFA Aire.
Esta exportación conserva el portal y las migraciones/Edge Functions. El receptor PC,
el firmware Arduino y la app Android permanecen en el proyecto principal.

Acceso por cuenta y aula; invitaciones por enlace privado/QR y contraseña propia.
No incluye secretos, sesiones, datos de mediciones ni cuentas de personas.
Firebase Hosting Spark y Supabase Free; sin facturación vinculada por este despliegue.

## Desarrollo

En `interfaz_web`: `npm ci` y `npm run build -- --mode hosting`.
Para preparar Hosting, proporcionar localmente `secrets/supabase-public.json`
con `url` y `key` pública anon/publishable. Nunca usar service_role.
Ejecutar `python herramientas/preparar_portal_publico.py`.
La publicación requiere una identidad propia autorizada en Firebase.

Para comprobar SQL local: `npm ci --prefix herramientas/sql-check` y
`node herramientas/sql-check/invitations.test.mjs`.
Las Edge Functions requieren secretos gestionados por Supabase; no están en Git.

Alcance, seguridad, correo y pruebas: [documentación](docs/PORTAL_PUBLICO_E_INVITACIONES.md).
''',encoding='utf-8')
(out/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Exportación de código preparada:',len(files),'archivos fuente; sin datos ni credenciales.')
