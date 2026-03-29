$ErrorActionPreference = 'SilentlyContinue'

$ports = @(8000, 8001)

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        Stop-Process -Id $conn.OwningProcess -Force
        Write-Host "Stopped process $($conn.OwningProcess) on port $port"
    }
}

$workerProcesses = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'run_(vision|multi_camera)_worker\.py' }

foreach ($proc in $workerProcesses) {
    Stop-Process -Id $proc.ProcessId -Force
    Write-Host "Stopped worker process $($proc.ProcessId)"
}

$backendProcesses = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -match '^python' -and
        $_.CommandLine -match 'app\.main:app' -and
        $_.CommandLine -match '--port\s+8001'
    }

foreach ($proc in $backendProcesses) {
    Stop-Process -Id $proc.ProcessId -Force
    Write-Host "Stopped backend process $($proc.ProcessId)"
}

$localJobs = Get-Job -Name 'ps5-*' -ErrorAction SilentlyContinue
foreach ($job in $localJobs) {
    Stop-Job -Id $job.Id -Force -ErrorAction SilentlyContinue
    Remove-Job -Id $job.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped local job $($job.Id)"
}

Write-Host 'Done.'
