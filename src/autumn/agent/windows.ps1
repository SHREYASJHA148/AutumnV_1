# Trusted convenience tools available to the local planner; ordinary account rights.
function Autumn-Element([string]$Id) {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($e in $all) {
        try { if (($e.GetRuntimeId() -join '.') -eq $Id) { return $e } } catch {}
    }
    throw 'Control changed or disappeared; inspect again before acting.'
}
function Autumn-Desktop([int]$ProcessId = 0) {
    Add-Type -AssemblyName UIAutomationClient
    Add-Type -AssemblyName UIAutomationTypes
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children, [System.Windows.Automation.Condition]::TrueCondition)
    $result = @()
    foreach ($w in $windows) {
        try {
            if ($ProcessId -and $w.Current.ProcessId -ne $ProcessId) { continue }
            if ($w.Current.IsOffscreen -or !$w.Current.Name) { continue }
            $controls = @()
            $all = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
            foreach ($e in $all) {
                try {
                    if ($e.Current.IsOffscreen -or $e.Current.IsPassword) { continue }
                    if (!$e.Current.Name -and $e.Current.ControlType.ProgrammaticName -ne 'ControlType.Edit') { continue }
                    $controls += @{id=($e.GetRuntimeId() -join '.');name=$e.Current.Name;type=$e.Current.ControlType.ProgrammaticName;enabled=$e.Current.IsEnabled}
                    if ($controls.Count -ge 35) { break }
                } catch {}
            }
            $result += @{title=$w.Current.Name;id=($w.GetRuntimeId() -join '.');controls=$controls}
            if ($result.Count -ge 6) { break }
        } catch {}
    }
    ConvertTo-Json -InputObject @($result) -Depth 5 -Compress
}
function Autumn-Click([string]$Id) {
    $e = Autumn-Element $Id
    if ($e.Current.IsPassword -or !$e.Current.IsEnabled) { throw 'Control is protected or disabled.' }
    $pattern = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) { $pattern.Invoke(); 'Invoked'; return }
    if ($e.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$pattern)) { $pattern.Select(); 'Selected'; return }
    if ($e.TryGetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern, [ref]$pattern)) { $pattern.Toggle(); 'Toggled'; return }
    throw 'This control has no supported UI Automation activation pattern.'
}
function Autumn-Type([string]$Id, [string]$Text) {
    $e = Autumn-Element $Id
    if ($e.Current.IsPassword -or !$e.Current.IsEnabled) { throw 'Control is protected or disabled.' }
    $pattern = $null
    if (!$e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$pattern) -or $pattern.Current.IsReadOnly) { throw 'This control does not support setting a text value.' }
    $pattern.SetValue($Text)
    $until = [DateTime]::UtcNow.AddMilliseconds(500)
    while ($pattern.Current.Value -ne $Text -and [DateTime]::UtcNow -lt $until) { Start-Sleep -Milliseconds 20 }
    if ($pattern.Current.Value -ne $Text) { throw 'Text delivery could not be verified; do not repeat automatically.' }
    'Text value verified; inspect before submitting it.'
}
function Autumn-Key([string]$Id, [string]$Keys) {
    $e = Autumn-Element $Id
    if ($e.Current.IsPassword -or !$e.Current.IsEnabled) { throw 'Control is protected or disabled.' }
    $e.SetFocus()
    $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
    if (($focused.GetRuntimeId() -join '.') -ne $Id) { throw 'Focus could not be verified; no key sent.' }
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait($Keys)
    'Keys sent once; inspect before any further action.'
}
