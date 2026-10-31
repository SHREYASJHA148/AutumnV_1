param([ValidateSet('run','test','lint','build')][string]$Task = 'run')
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskPython = Join-Path $taskRoot '.venv-qt-compat/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $taskRoot 'src'
Push-Location -LiteralPath $taskRoot
try {
    switch ($Task) {
        'run' { & $taskPython -m autumn.main }
        'test' { & $taskPython -m pytest }
        'lint' { & $taskPython -m ruff check }
        'build' { & (Join-Path $taskRoot 'packaging/build.ps1') }
    }
    $taskExit = $LASTEXITCODE
} finally { Pop-Location }
exit $taskExit
