$ErrorActionPreference = "Stop"
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$project = Split-Path -Parent $PSScriptRoot
$testFolder = Join-Path $env:TEMP "file_organizer_browser_target"
$browserProfile = Join-Path $env:TEMP "file_organizer_edge_profile"
$stdoutLog = Join-Path $env:TEMP "file_organizer_browser_stdout.log"
$stderrLog = Join-Path $env:TEMP "file_organizer_browser_stderr.log"
$batchFile = Join-Path $project "start_web.bat"
$server = $null
$edge = $null

function Wait-ForElement($root, $property, $value, $seconds = 15) {
    $condition = [System.Windows.Automation.PropertyCondition]::new($property, $value)
    $deadline = (Get-Date).AddSeconds($seconds)
    do {
        $element = $root.FindFirst(
            [System.Windows.Automation.TreeScope]::Descendants,
            $condition
        )
        if ($element) { return $element }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    return $null
}

function Invoke-Element($element) {
    $pattern = $element.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    )
    $pattern.Invoke()
}

Remove-Item $testFolder, $browserProfile -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $testFolder | Out-Null
Set-Content -Path (Join-Path $testFolder "sample.txt") -Value "browser preview test" -Encoding UTF8

$edgePaths = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    (Join-Path $env:LOCALAPPDATA "Microsoft\Edge\Application\msedge.exe")
)
$edgePath = $edgePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $edgePath) { throw "Microsoft Edge was not found." }

try {
    $env:FILE_ORGANIZER_NO_BROWSER = "1"
    $env:FILE_ORGANIZER_PICKER_INITIAL_DIR = $testFolder

    $serverInfo = New-Object System.Diagnostics.ProcessStartInfo
    $serverInfo.FileName = $env:ComSpec
    $serverInfo.Arguments = "/d /c call `"$batchFile`""
    $serverInfo.WorkingDirectory = $project
    $serverInfo.UseShellExecute = $false
    $serverInfo.CreateNoWindow = $true
    $serverInfo.RedirectStandardOutput = $true
    $serverInfo.RedirectStandardError = $true
    $serverInfo.EnvironmentVariables["FILE_ORGANIZER_NO_BROWSER"] = "1"
    $serverInfo.EnvironmentVariables["FILE_ORGANIZER_PICKER_INITIAL_DIR"] = $testFolder
    $server = New-Object System.Diagnostics.Process
    $server.StartInfo = $serverInfo
    [void]$server.Start()

    $deadline = (Get-Date).AddSeconds(20)
    $health = $null
    do {
        Start-Sleep -Milliseconds 250
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2
        } catch {
            $health = $null
        }
    } while ($health.status -ne "ok" -and (Get-Date) -lt $deadline)
    if ($health.status -ne "ok") { throw "start_web.bat did not start the server." }
    Write-Output "APP_STARTED:OK"

    $edge = Start-Process -FilePath $edgePath `
        -ArgumentList @(
            "--user-data-dir=$browserProfile",
            "--no-first-run",
            "--disable-features=msEdgeFirstRunExperience",
            "--app=http://127.0.0.1:5000"
        ) `
        -PassThru

    $desktop = [System.Windows.Automation.AutomationElement]::RootElement
    $window = Wait-ForElement $desktop `
        ([System.Windows.Automation.AutomationElement]::NameProperty) `
        "File Organizer" 20
    if (-not $window) { throw "The File Organizer browser window was not found." }

    $selectButton = Wait-ForElement $window `
        ([System.Windows.Automation.AutomationElement]::AutomationIdProperty) `
        "selectFolderButton" 15
    if (-not $selectButton) { throw "The folder selection button was not found." }

    $pythonBefore = @(
        Get-Process python -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty Id
    )
    Invoke-Element $selectButton

    $pickerDeadline = (Get-Date).AddSeconds(12)
    $picker = $null
    do {
        Start-Sleep -Milliseconds 250
        $picker = Get-Process python -ErrorAction SilentlyContinue |
            Where-Object { $_.Id -notin $pythonBefore } |
            Select-Object -First 1
    } while (-not $picker -and (Get-Date) -lt $pickerDeadline)
    if (-not $picker) { throw "The folder picker process was not started from the browser button." }

    $shell = New-Object -ComObject WScript.Shell
    if (-not $shell.AppActivate($picker.Id)) {
        throw "The Windows folder selection dialog could not be activated."
    }
    Write-Output "FOLDER_BUTTON_AND_DIALOG:OK"
    Start-Sleep -Milliseconds 500
    $shell.SendKeys("{ENTER}")

    $pathInput = Wait-ForElement $window `
        ([System.Windows.Automation.AutomationElement]::AutomationIdProperty) `
        "folderPath" 12
    if (-not $pathInput) { throw "The selected folder field was not found." }
    $valuePattern = $pathInput.GetCurrentPattern(
        [System.Windows.Automation.ValuePattern]::Pattern
    )
    $valueDeadline = (Get-Date).AddSeconds(12)
    $selectedValue = ""
    do {
        Start-Sleep -Milliseconds 250
        $selectedValue = $valuePattern.Current.Value
    } while (-not $selectedValue -and (Get-Date) -lt $valueDeadline)
    if (-not $selectedValue) { throw "The selected folder was not reflected in the browser." }
    Write-Output ("FOLDER_FIELD_VALUE:" + $selectedValue)
    $selectedPath = [System.IO.Path]::GetFullPath($selectedValue.Replace("/", "\")).TrimEnd("\")
    $expectedPath = [System.IO.Path]::GetFullPath($testFolder).TrimEnd("\")
    if ($selectedPath -ne $expectedPath) {
        throw "The selected folder was not shown in the browser: $selectedPath"
    }
    Write-Output ("FOLDER_SELECTED_IN_UI:OK " + $selectedPath)

    $previewButton = Wait-ForElement $window `
        ([System.Windows.Automation.AutomationElement]::AutomationIdProperty) `
        "previewButton" 10
    if (-not $previewButton) { throw "The preview button was not found." }
    Invoke-Element $previewButton

    $sampleCell = Wait-ForElement $window `
        ([System.Windows.Automation.AutomationElement]::NameProperty) `
        "sample.txt" 12
    if (-not $sampleCell) { throw "sample.txt was not displayed in the preview." }
    Write-Output "PREVIEW_VISIBLE_IN_UI:OK sample.txt"
}
finally {
    Remove-Item Env:FILE_ORGANIZER_NO_BROWSER -ErrorAction SilentlyContinue
    Remove-Item Env:FILE_ORGANIZER_PICKER_INITIAL_DIR -ErrorAction SilentlyContinue

    if ($browserProfile) {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*$browserProfile*" } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }

    Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    if ($server -and -not $server.HasExited) {
        Stop-Process -Id $server.Id -Force -ErrorAction SilentlyContinue
    }

    if ($server) {
        $stdout = $server.StandardOutput.ReadToEnd()
        $stderr = $server.StandardError.ReadToEnd()
        Set-Content -Path $stdoutLog -Value $stdout -Encoding UTF8
        Set-Content -Path $stderrLog -Value $stderr -Encoding UTF8
        if ($stdout) { Write-Output $stdout.Trim() }
        if ($stderr) { Write-Output $stderr.Trim() }
    }

    Remove-Item $testFolder, $browserProfile -Recurse -Force -ErrorAction SilentlyContinue
}
