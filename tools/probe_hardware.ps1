param([string]$OutputPath = (Join-Path $PSScriptRoot '../docs/reports/hardware_inventory.json'))
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskOutput = [IO.Path]::GetFullPath($OutputPath)
if (-not $taskOutput.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Inventory output must remain inside the project.'
}
$taskFacts = [ordered]@{
    CapturedUtc = [DateTime]::UtcNow.ToString('o')
    OS = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber
    RAM_GiB = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
    CPU = (Get-CimInstance Win32_Processor).Name
    GPU = @(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion)
    Disk = @(Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{n='Free_GiB';e={[math]::Round($_.Free/1GB,1)}})
    AudioEndpoints = @(Get-PnpDevice -Class AudioEndpoint -PresentOnly | Select-Object FriendlyName, Status)
    Tools = @(Get-Command python, py, ollama, git -ErrorAction SilentlyContinue | Select-Object Name, Source)
    OllamaProcesses = @(Get-Process -Name '*ollama*' -ErrorAction SilentlyContinue | Select-Object ProcessName, Id)
}
$taskFacts | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $taskOutput -Encoding utf8
Write-Output "Inventory saved to $taskOutput"
