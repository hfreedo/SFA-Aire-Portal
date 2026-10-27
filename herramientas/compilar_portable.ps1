param([switch]$SkipPackage)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$sfaIcon = (Resolve-Path -LiteralPath 'Branding/logo/sfa-aire.ico').Path
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile --console --icon $sfaIcon --name SFA_Aire_Receptor --distpath artifacts/portable-bin --workpath artifacts/portable-worker-build --specpath artifacts --paths . --paths herramientas --hidden-import servidor_pc.main --hidden-import firebase_admin.messaging --hidden-import serial.tools.list_ports_windows --hidden-import apk_release --collect-submodules uvicorn --copy-metadata firebase-admin herramientas/portable_worker.py
if ($LASTEXITCODE -ne 0) { throw 'Falló el receptor portable' }
& .venv/Scripts/python.exe -m PyInstaller --noconfirm --onefile --windowed --icon $sfaIcon --name 'Panel SFA Aire' --distpath artifacts/portable-bin --workpath artifacts/portable-panel-build --specpath artifacts panel_inicio.py
if ($LASTEXITCODE -ne 0) { throw 'Falló el panel portable' }
if (-not $SkipPackage) {
& .venv/Scripts/python.exe herramientas/empaquetar_portable.py
if ($LASTEXITCODE -ne 0) { throw 'Falló la validación del paquete' }
}
