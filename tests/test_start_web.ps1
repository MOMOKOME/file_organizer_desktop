$ErrorActionPreference = "Stop"

$project = Split-Path -Parent $PSScriptRoot
$batchFile = Join-Path $project "start_web.bat"
$stdoutLog = Join-Path $env:TEMP "file_organizer_start_web_stdout.log"
$stderrLog = Join-Path $env:TEMP "file_organizer_start_web_stderr.log"
$process = $null

if (Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue) {
    throw "Port 5000 is already in use."
}

Remove-Item $stdoutLog, $stderrLog -Force -ErrorAction SilentlyContinue

try {
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $env:ComSpec
    $startInfo.Arguments = "/d /c call `"$batchFile`""
    $startInfo.WorkingDirectory = $project
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.EnvironmentVariables["FILE_ORGANIZER_NO_BROWSER"] = "1"

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()

    $deadline = (Get-Date).AddSeconds(20)
    $health = $null
    while ((Get-Date) -lt $deadline) {
        if ($process.HasExited) {
            break
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 2
            if ($health.status -eq "ok") {
                break
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }

    if ($null -eq $health -or $health.status -ne "ok") {
        throw "start_web.bat did not start a healthy server within 20 seconds."
    }

    Write-Output "START_WEB_HEALTH_CHECK:OK"
    Write-Output "URL:http://127.0.0.1:5000"
}
finally {
    $listener = Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        $listener | Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    }

    if ($process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }

    if ($process) {
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
        Set-Content -Path $stdoutLog -Value $stdout -Encoding UTF8
        Set-Content -Path $stderrLog -Value $stderr -Encoding UTF8
        if ($stdout) { Write-Output $stdout.Trim() }
        if ($stderr) { Write-Output $stderr.Trim() }
    }
}
