$ErrorActionPreference = 'SilentlyContinue'

$ports = @(8000, 8001)

foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen
    foreach ($conn in $connections) {
        Stop-Process -Id $conn.OwningProcess -Force
        Write-Host "Stopped process $($conn.OwningProcess) on port $port"
    }
}

Write-Host 'Done.'
