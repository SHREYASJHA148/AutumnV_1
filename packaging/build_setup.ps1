$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv-qt-compat/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $taskRoot 'src'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $taskRoot '.cache/pyinstaller-phase7-setup'
$taskOutput = Join-Path $taskRoot 'dist/Autumn-0.7.2-preview'
& $taskPython (Join-Path $PSScriptRoot 'release_payload.py')
if ($LASTEXITCODE -ne 0) { exit 1 }
$taskPayload = Join-Path $taskOutput 'payload.zip'
$taskMetadata = Join-Path $taskOutput 'installer-metadata.json'
$taskNotices = Join-Path $taskRoot 'THIRD_PARTY_NOTICES.md'
& $taskPython -m PyInstaller --clean --noconfirm --onefile --windowed --name AutumnSetup `
    --paths (Join-Path $taskRoot 'src') --add-data "${taskPayload};." `
    --add-data "${taskMetadata};." --add-data "${taskNotices};." `
    --distpath $taskOutput --workpath (Join-Path $taskRoot 'build/setup') `
    --specpath (Join-Path $taskRoot 'build') (Join-Path $PSScriptRoot 'setup_launch.py') *> (Join-Path $taskRoot '.cache/phase7-setup-build.log')
if ($LASTEXITCODE -ne 0) { Get-Content (Join-Path $taskRoot '.cache/phase7-setup-build.log') -Tail 15; exit 1 }
Write-Output 'AutumnSetup.exe created in dist/Autumn-0.7.2-preview.'
