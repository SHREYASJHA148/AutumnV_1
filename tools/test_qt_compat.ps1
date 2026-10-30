# Run after installing requirements-qt-compat.lock into .venv-qt-compat.
# This is a disposable Phase 0 probe, not an Autumn product build.
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv-qt-compat/Scripts/python.exe'
$env:AUTUMN_PROBE_ROOT = $taskRoot
$env:QT_QUICK_BACKEND = 'software'
$env:QML_DISABLE_DISK_CACHE = '1'
$env:PYINSTALLER_CONFIG_DIR = Join-Path $taskRoot '.cache/pyinstaller-qt-compat'
$taskStarted = [DateTime]::UtcNow
$taskResult = [ordered]@{
    experiment = 'CPython 3.12.10 + PySide6-Essentials 6.8.3 + PyInstaller 6.22.3'
    started_utc = $taskStarted.ToString('o')
    source_exit_code = $null
    build_exit_code = $null
    frozen_exit_code = $null
    dll_patches = 0
}
$taskReport = Join-Path $taskRoot 'docs/reports/qt_compat_trial.json'
try {
    $env:AUTUMN_PROBE_REPORT = 'qt_compat_source.json'
    & $taskPython (Join-Path $taskRoot 'tools/phase0_qt_smoke.py')
    $taskResult.source_exit_code = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) { throw 'Compatibility source probe failed' }
    $taskDist = Join-Path $taskRoot 'dist/qt compatibility é'
    $taskLog = Join-Path $taskRoot '.cache/qt-compat-build.log'
    & $taskPython -m PyInstaller --noconfirm --onedir --console --name AutumnQtCompat `
        --distpath $taskDist --workpath (Join-Path $taskRoot 'build/qt-compat') `
        --specpath (Join-Path $taskRoot 'build') (Join-Path $taskRoot 'tools/phase0_qt_smoke.py') *> $taskLog
    $taskResult.build_exit_code = $LASTEXITCODE
    if ($LASTEXITCODE -ne 0) {
        Get-Content -LiteralPath $taskLog -Tail 15
        throw 'Compatibility standalone build failed'
    }
    $taskExecutable = Join-Path $taskDist 'AutumnQtCompat/AutumnQtCompat.exe'
    $env:AUTUMN_PROBE_REPORT = 'qt_compat_frozen.json'
    Push-Location -LiteralPath (Split-Path -Parent $taskExecutable)
    try {
        & $taskExecutable
        $taskResult.frozen_exit_code = $LASTEXITCODE
    } finally { Pop-Location }
    $taskResult.executable_sha256 = (Get-FileHash -LiteralPath $taskExecutable -Algorithm SHA256).Hash
    if ($taskResult.frozen_exit_code -ne 0) { throw 'Compatibility standalone launch failed' }
    foreach ($taskName in @('qt_compat_source.json', 'qt_compat_frozen.json')) {
        $taskFile = Get-Item -LiteralPath (Join-Path $taskRoot "docs/reports/$taskName")
        if ($taskFile.LastWriteTimeUtc -lt $taskStarted) { throw 'Stale probe report' }
        $taskEvidence = Get-Content -LiteralPath $taskFile.FullName -Raw | ConvertFrom-Json
        foreach ($taskCheck in @('qml_loaded', 'tray_available', 'fixture_has_foreground', 'overlay_preserves_foreground')) {
            if (-not $taskEvidence.$taskCheck) { throw "Probe check did not pass: $taskCheck" }
        }
        if ($taskEvidence.python_version -ne '3.12.10' -or $taskEvidence.qt_version -ne '6.8.3') {
            throw 'Unexpected runtime versions'
        }
    }
    $taskResult.result = 'pass'
} catch {
    $taskResult.result = 'fail'
    $taskResult.error = $_.Exception.Message
} finally {
    $taskResult.elapsed_seconds = [math]::Round(([DateTime]::UtcNow - $taskStarted).TotalSeconds, 2)
    $taskResult | ConvertTo-Json | Set-Content -LiteralPath $taskReport -Encoding utf8
}
Write-Output "Qt compatibility experiment: $($taskResult.result)"
if ($taskResult.result -ne 'pass') { exit 1 }
