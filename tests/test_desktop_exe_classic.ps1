# File Organizer Classic exe check (Simple's tests/test_desktop_exe.ps1 is unchanged).
# Same flow as Simple, plus: Classic-only bundle, history view navigation, and the lock
# shared with the Simple exe (both editions use the same data folder and desktop.lock).
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class DesktopTestNative {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd, uint msg, IntPtr wParam, IntPtr lParam);
}
'@
$project = Split-Path -Parent $PSScriptRoot
$run = Join-Path $project ('.verification-desktop/classic-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run -Force | Out-Null
$oldLocal = $env:LOCALAPPDATA
$env:LOCALAPPDATA = Join-Path $run 'LocalAppData'
$exe = Join-Path $project 'dist/File Organizer Classic/File Organizer Classic.exe'
$simpleExe = Join-Path $project 'dist/File Organizer/File Organizer.exe'
$simple = $null
$app = $null
$second = $null
$report = [ordered]@{run=$run}
$bundle = Join-Path $project 'dist/File Organizer Classic/_internal'
if ((Get-Content -Raw (Join-Path $bundle 'edition.txt')).Trim() -ne 'classic') { throw 'Edition marker missing' }
if (Test-Path (Join-Path $bundle 'templates/index.html')) { throw 'Simple template shipped in Classic' }
if (Test-Path (Join-Path $bundle 'static/style.css')) { throw 'Simple stylesheet shipped in Classic' }
$report.classicOnlyBundle = $true
function Wait-Window($process) {
    for ($i=0; $i -lt 120; $i++) {
        $process.Refresh()
        if ($process.HasExited) { throw 'EXE exited during startup' }
        if ($process.MainWindowHandle -ne 0) { return $process.MainWindowHandle }
        Start-Sleep -Milliseconds 250
    }
    throw 'No application window after 30 seconds'
}
function Post-Json($url, $data) {
    Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/json' -Body ($data | ConvertTo-Json -Compress)
}
function Find-Ui($root, $property, $value, $seconds = 10) {
    $condition = [System.Windows.Automation.PropertyCondition]::new($property, $value)
    $deadline = (Get-Date).AddSeconds($seconds)
    do {
        $element = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
        if ($element) { return $element }
        Start-Sleep -Milliseconds 100
    } while ((Get-Date) -lt $deadline)
    throw "UI element missing: $value"
}
function Invoke-Ui($element) {
    Wait-UiEnabled $element
    Write-Output ('INVOKE: ' + $element.Current.Name + ' / ' + $element.Current.AutomationId)
    $pattern = $null
    if ($element.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$pattern)) { $pattern.Invoke() }
    else { $element.GetCurrentPattern([System.Windows.Automation.LegacyIAccessiblePattern]::Pattern).DoDefaultAction() }
}
function Find-Button($root, $name) {
    $condition = [System.Windows.Automation.AndCondition]::new(
        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::NameProperty, $name),
        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button))
    $button = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $condition)
    if (-not $button) { throw "Button missing: $name" }
    return $button
}
function Wait-UiEnabled($element) {
    for ($i=0; $i -lt 100; $i++) {
        if ($element.Current.IsEnabled) { return }
        Start-Sleep -Milliseconds 100
    }
    throw 'UI element remained disabled'
}
try {
    $app = Start-Process -FilePath $exe -PassThru -WindowStyle Normal
    $report.appId = $app.Id
    $handle = Wait-Window $app
    $report.windowTitle = $app.MainWindowTitle
    if ($app.MainWindowTitle -notlike 'File Organizer Classic *') { throw 'Startup error dialog instead of app' }
    $connections = @(Get-NetTCPConnection -OwningProcess $app.Id -State Listen)
    if ($connections.Count -ne 1 -or $connections[0].LocalAddress -ne '127.0.0.1') { throw 'Unexpected listening address' }
    $url = 'http://127.0.0.1:' + $connections[0].LocalPort
    $report.listen = $url
    $root = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $names = @()
    for ($i=0; $i -lt 60; $i++) {
        $elements = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        $names = @($elements | ForEach-Object { $_.Current.Name })
        if ($names -contains '整理予定を見る') { break }
        Start-Sleep -Milliseconds 250
    }
    $report.uiNames = $names
    if ($names -notcontains '整理予定を見る') { throw 'UI preview control was not rendered' }
    $report.uiRendered = $true
    foreach ($resource in @('/static/app.js', '/static/classic/classic.css', '/static/classic/classic.js', '/static/classic/botanical/sidebar.svg')) {
        if ((Invoke-WebRequest -UseBasicParsing ($url + $resource)).StatusCode -ne 200) { throw ('Static resource missing: ' + $resource) }
    }
    if ((Invoke-WebRequest -UseBasicParsing $url).Content -notmatch 'data-theme="classic"') { throw 'Classic screen not served' }
    $report.classicScreenServed = $true
    $folder = Join-Path $run 'files'
    New-Item -ItemType Directory -Path $folder | Out-Null
    [IO.File]::WriteAllText((Join-Path $folder 'sample.txt'), 'temporary desktop exe content')
    $preview = Post-Json ($url + '/api/preview') @{folder=$folder}
    $job = Post-Json ($url + '/api/jobs') @{preview_id=$preview.preview_id}
    for ($i=0; $i -lt 100; $i++) {
        $status = Invoke-RestMethod ($url + '/api/jobs/' + $job.job_id)
        if ($status.status -eq 'completed') { break }
        if ($status.status -eq 'failed') { throw 'Organization failed' }
        Start-Sleep -Milliseconds 100
    }
    if ($status.status -ne 'completed') { throw 'Organization timed out' }
    $history = Invoke-RestMethod ($url + '/api/history')
    if ($history.history.Count -ne 1) { throw 'History missing' }
    $undo = Post-Json ($url + '/api/history/' + $job.job_id + '/undo') @{confirmed=$true}
    if ($undo.success_count -ne 1 -or [IO.File]::ReadAllText((Join-Path $folder 'sample.txt')) -ne 'temporary desktop exe content') { throw 'Undo failed' }
    $report.previewOrganizeHistoryUndo = $true
    $report.localAppDataDb = Test-Path (Join-Path $env:LOCALAPPDATA 'MOMONGA_Lab/FileOrganizer/state.sqlite3')
    # Use actual controls in the embedded WebView, including native folder dialog.
    $idProperty = [System.Windows.Automation.AutomationElement]::AutomationIdProperty
    Invoke-Ui (Find-Ui $root $idProperty 'selectFolderButton')
    $dialog = $null
    $dialogCondition = [System.Windows.Automation.AndCondition]::new(
        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ClassNameProperty, '#32770'),
        [System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty, [int]$app.Id))
    for ($i=0; $i -lt 100; $i++) {
        $dialog = [System.Windows.Automation.AutomationElement]::RootElement.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $dialogCondition)
        if ($dialog) { break }
        Start-Sleep -Milliseconds 100
    }
    if (-not $dialog) { throw 'App native folder dialog not found' }
    # Shell folder dialogs expose different UIA patterns across Windows builds.
    # WM_CLOSE is the standard cancel action, scoped to this app-owned dialog.
    $null = [DesktopTestNative]::PostMessage([IntPtr]$dialog.Current.NativeWindowHandle, 0x10, [IntPtr]::Zero, [IntPtr]::Zero)
    $report.nativeFolderDialogOpenedCancelled = $true
    $pathElement = Find-Ui $root $idProperty 'folderPath'
    Wait-UiEnabled $pathElement
    $pathElement.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($folder)
    Invoke-Ui (Find-Ui $root $idProperty 'previewButton')
    $null = Find-Ui $root ([System.Windows.Automation.AutomationElement]::NameProperty) 'sample.txt'
    Invoke-Ui (Find-Ui $root $idProperty 'organizeButton')
    Invoke-Ui (Find-Ui $root $idProperty 'confirmStartButton')
    $null = Find-Ui $root ([System.Windows.Automation.AutomationElement]::NameProperty) '整理が完了しました'
    if (-not (Test-Path (Join-Path $folder 'txt/sample.txt'))) { throw 'GUI organization did not move sample' }
    # Undo lives in the history view: use the result footer link (navigation only).
    Invoke-Ui (Find-Button $root '履歴')
    $null = Find-Ui $root ([System.Windows.Automation.AutomationElement]::NameProperty) '直前の整理'
    $report.historyViewNavigation = $true
    Invoke-Ui (Find-Ui $root $idProperty 'undoLatest')
    $undoDialog = Find-Ui $root $idProperty 'undoDialog'
    Invoke-Ui (Find-Button $undoDialog '元に戻す')
    for ($i=0; $i -lt 100; $i++) {
        if (Test-Path (Join-Path $folder 'sample.txt')) { break }
        Start-Sleep -Milliseconds 100
    }
    if ([IO.File]::ReadAllText((Join-Path $folder 'sample.txt')) -ne 'temporary desktop exe content') { throw 'GUI Undo failed' }
    $report.guiPreviewOrganizeUndo = $true
    Add-Type -AssemblyName System.Drawing
    $bounds = $root.Current.BoundingRectangle
    $bitmap = [Drawing.Bitmap]::new([int]$bounds.Width, [int]$bounds.Height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen([int]$bounds.X, [int]$bounds.Y, 0, 0, $bitmap.Size)
        $bitmap.Save((Join-Path $run 'desktop-window-classic.png'))
    } finally { $graphics.Dispose(); $bitmap.Dispose() }
    $report.windowScreenshot = Join-Path $run 'desktop-window-classic.png'
    $second = Start-Process -FilePath $exe -PassThru -WindowStyle Normal
    $secondHandle = Wait-Window $second
    $secondRoot = [System.Windows.Automation.AutomationElement]::FromHandle($secondHandle)
    $secondElements = $secondRoot.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
    $secondNames = @($secondElements | ForEach-Object { $_.Current.Name })
    if (-not ($secondNames -match 'すでに起動')) { throw 'Duplicate instance warning missing' }
    $null = $second.CloseMainWindow()
    if (-not $second.WaitForExit(10000)) { throw 'Second instance did not exit' }
    $report.duplicateRejected = $true
    # The Simple exe shares the data folder and desktop.lock, so it must refuse to start too.
    if (Test-Path $simpleExe) {
        $simple = Start-Process -FilePath $simpleExe -PassThru -WindowStyle Normal
        $simpleHandle = Wait-Window $simple
        $simpleRoot = [System.Windows.Automation.AutomationElement]::FromHandle($simpleHandle)
        $simpleElements = $simpleRoot.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
        $simpleNames = @($simpleElements | ForEach-Object { $_.Current.Name })
        if (-not ($simpleNames -match 'すでに起動')) { throw 'Simple exe started while Classic was running' }
        $null = $simple.CloseMainWindow()
        if (-not $simple.WaitForExit(10000)) { throw 'Simple instance did not exit' }
        $report.simpleRejectedWhileClassicRuns = $true
    } else { $report.simpleRejectedWhileClassicRuns = 'not checked: Simple exe not built' }
    $snapshot = @(Get-CimInstance Win32_Process)
    $ownedIds = @($app.Id)
    do {
        $newIds = @($snapshot | Where-Object { $_.ParentProcessId -in $ownedIds -and $_.ProcessId -notin $ownedIds } | ForEach-Object { $_.ProcessId })
        $ownedIds += $newIds
    } while ($newIds.Count -gt 0)
    $report.processTreeIds = $ownedIds
    $null = $app.CloseMainWindow()
    if (-not $app.WaitForExit(15000)) { throw 'App did not shut down normally' }
    $report.exitCode = $app.ExitCode
    if ($app.ExitCode -ne 0) { throw 'Nonzero app exit' }
    $left = @(Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -in $ownedIds })
    $report.residualProcesses = $left.Count
    if ($left.Count -ne 0) { throw 'Residual processes found' }
    $report.success = $true
} catch {
    $report.success = $false
    $report.error = $_.Exception.Message
    throw
} finally {
    $env:LOCALAPPDATA = $oldLocal
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $run 'result.json')
    Write-Output ($report | ConvertTo-Json -Depth 8)
    foreach ($process in @($simple, $second, $app)) {
        if ($process -and -not $process.HasExited) {
            if ($dialog -and $process.Id -eq $app.Id) {
                try { $null = [DesktopTestNative]::PostMessage([IntPtr]$dialog.Current.NativeWindowHandle, 0x10, [IntPtr]::Zero, [IntPtr]::Zero) } catch { }
            }
            $null = $process.CloseMainWindow()
        }
    }
}
