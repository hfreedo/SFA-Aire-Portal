"""Paquete revisable de fuentes, interfaz construida y APK; nunca datos o secretos."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Entregas'
ARCHIVE = OUT / 'SFA_Aire_Base_Integrada_0.5.0.zip'
ROOT_FILES = ['README.md', 'AGENTS.md', '.gitignore', 'iniciar.py', 'iniciar_pc.bat',
              'iniciar_red_local.bat', 'iniciar_portal_remoto.bat', 'preparar_entorno.bat', 'compilar_android.ps1']
TREE_ROOTS = ['docs', 'arduino', 'servidor_pc', 'tests', 'herramientas', 'interfaz_web', 'android_app', 'supabase']
BLOCKED_PARTS = {'node_modules', '.gradle', '.kotlin', '__pycache__', 'build', '.git',
                 'data', 'secrets', '.venv', 'artifacts', '.temp'}
BLOCKED_FILES = {'google-services.json', 'local.properties', '.env', 'supabase-pc.json', 'sfa-public.json'}


def allowed(path):
    rel = path.relative_to(ROOT)
    # "data" es también un paquete de código Kotlin. La excepción se limita al
    # árbol de fuentes Android/web; no permite carpetas de datos de ejecución.
    source_data = (len(rel.parts) >= 9 and rel.parts[:3] == ('android_app', 'app', 'src')
                   and rel.parts[3] in {'main', 'test', 'androidTest'}
                   and rel.parts[4:9] == ('java', 'org', 'sfa', 'aire', 'data')) or rel.parts[:3] == ('interfaz_web','src','data')
    blocked = BLOCKED_PARTS - {'data'} if source_data else BLOCKED_PARTS
    return not any(part in blocked for part in rel.parts) and path.name not in BLOCKED_FILES and path.suffix not in {'.pyc', '.jks', '.keystore'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    files = [ROOT / name for name in ROOT_FILES]
    for folder in TREE_ROOTS:
        for path in (ROOT / folder).rglob('*'):
            if path.is_file() and allowed(path):
                files.append(path)
    combined=OUT/'Supabase_SFA_Aire_v05_nuevo_proyecto.sql'
    combined.write_text('-- SOLO PROYECTO NUEVO. Si tiene v0.4 (001+002+003), aplique únicamente 004.\n'+
        '\n'.join(path.read_text(encoding='utf-8-sig') for path in sorted((ROOT/'supabase/migrations').glob('*.sql'))),encoding='utf-8')
    files += [OUT / 'SFA_Aire_0.5.0_prototipo.apk', OUT / 'Panel_alerta_simulada.png',
              OUT / 'Laboratorio_v03_demo.png',OUT / 'Laboratorio_v03_controles_demo.png',
              OUT / 'Laboratorio_v03_traza_demo.png',
              OUT / 'Coordinacion_v04_demo.png',OUT / 'Coordinacion_v04_indicacion_demo.png',
              OUT / 'Reservas_v05_demo.png',OUT / 'VERIFICACION_v05.json',combined]
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
    with zipfile.ZipFile(ARCHIVE, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, 'SFA_Aire/' + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        assert all(allowed(ROOT / Path(name).relative_to('SFA_Aire')) for name in archive.namelist())
        manifest = {path.relative_to(ROOT).as_posix(): sha(path) for path in files}
        for name,digest in manifest.items():
            assert hashlib.sha256(archive.read('SFA_Aire/'+name)).hexdigest() == digest
    (OUT / 'PAQUETE_v05_SHA256.json').write_text(json.dumps({
        'archive': ARCHIVE.name, 'sha256': sha(ARCHIVE), 'file_count': len(files),
        'archive_integrity': 'ok', 'secret_paths_excluded': True, 'files': manifest
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{ARCHIVE.name}: {len(files)} archivos, ZIP y digests verificados, {ARCHIVE.stat().st_size} bytes')


if __name__ == '__main__':
    main()
