$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv-qt-compat/Scripts/python.exe'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $taskRoot '.cache/pyinstaller-phase1'
$env:PYTHONPATH = Join-Path $taskRoot 'src'
$taskLog = Join-Path $taskRoot '.cache/phase6-build.log'
$taskDist = Join-Path $taskRoot 'dist/Autumn preview é'
$taskAssets = Join-Path $taskRoot '.cache/external_assets.json'
@{ development_models = (Join-Path $taskRoot 'models') } | ConvertTo-Json | Set-Content -LiteralPath $taskAssets -Encoding utf8
& $taskPython -m PyInstaller --clean --noconfirm --onedir --windowed --name Autumn `
    --paths (Join-Path $taskRoot 'src') --collect-data autumn `
    --additional-hooks-dir (Join-Path $taskRoot 'packaging/hooks') `
    --collect-all piper --collect-all pywhispercpp --collect-all _sounddevice_data `
    --collect-all openwakeword `
    --collect-all webrtcvad --hidden-import _webrtcvad `
    --add-data "${taskAssets};autumn/speech" `
    --add-data "$(Join-Path $taskRoot 'src/autumn/ui/Main.qml');autumn/ui" `
    --distpath $taskDist --workpath (Join-Path $taskRoot 'build/phase1') `
    --specpath (Join-Path $taskRoot 'build') (Join-Path $PSScriptRoot 'launch.py') *> $taskLog
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $taskLog -Tail 18; exit 1 }
Copy-Item -LiteralPath (Join-Path $taskRoot 'src/autumn/ui/Main.qml') -Destination (Join-Path $taskDist 'Autumn/_internal/autumn/ui/Main.qml')
Write-Output 'Autumn standalone build created in dist/Autumn preview é/Autumn.'
