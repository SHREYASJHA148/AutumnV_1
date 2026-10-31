$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv-qt-compat/Scripts/python.exe'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $taskRoot '.cache/pyinstaller-phase1'
$env:PYTHONPATH = Join-Path $taskRoot 'src'
$taskLog = Join-Path $taskRoot '.cache/phase1-build.log'
$taskDist = Join-Path $taskRoot 'dist/Autumn preview é'
& $taskPython -m PyInstaller --noconfirm --onedir --windowed --name Autumn `
    --paths (Join-Path $taskRoot 'src') --collect-data autumn `
    --add-data "$(Join-Path $taskRoot 'src/autumn/ui/Main.qml');autumn/ui" `
    --distpath $taskDist --workpath (Join-Path $taskRoot 'build/phase1') `
    --specpath (Join-Path $taskRoot 'build') (Join-Path $PSScriptRoot 'launch.py') *> $taskLog
if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $taskLog -Tail 18; exit 1 }
Write-Output 'Autumn standalone build created in dist/Autumn preview é/Autumn.'
