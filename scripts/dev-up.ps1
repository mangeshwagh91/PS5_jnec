param(
    [switch]$WithWorkers
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot 'server'
$clientPath = Join-Path $repoRoot 'client'
$venvActivate = Join-Path $repoRoot '.venv\Scripts\Activate.ps1'
$serverEnvPath = Join-Path $backendPath '.env'

if (-not (Test-Path $venvActivate)) {
    Write-Error "Python virtual environment not found at $venvActivate"
}

if (-not (Test-Path $serverEnvPath)) {
    Write-Error "Missing server .env at $serverEnvPath"
}

$ingestionApiKey = ''
Get-Content $serverEnvPath | ForEach-Object {
    if ($_ -match '^INGESTION_API_KEY=(.*)$') {
        $ingestionApiKey = $Matches[1]
    }
}

Write-Host 'Starting backend on http://localhost:8001 ...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$backendPath'; & '$venvActivate'; uvicorn app.main:app --reload --host 0.0.0.0 --port 8001"
)

Write-Host 'Starting frontend on http://localhost:8000 ...'
Start-Process powershell -ArgumentList @(
    '-NoExit',
    '-Command',
    "Set-Location '$clientPath'; npm run dev"
)

if ($WithWorkers) {
    if ([string]::IsNullOrWhiteSpace($ingestionApiKey)) {
        Write-Error 'INGESTION_API_KEY is empty in server/.env. Set it before starting workers.'
    }

    # Model-video matrix: every model is run on every demo video.
    $workerMatrix = @(
        @{ CameraId = 'CAM-012'; Location = 'Gate B North'; Weights = 'models/weapon_best.pt'; Stream = '..\\videos\\Firing.mp4' },
        @{ CameraId = 'CAM-013'; Location = 'Parking Lot C'; Weights = 'models/smoke_fire.pt'; Stream = '..\\videos\\smoke_fire.mp4' },
        @{ CameraId = 'CAM-014'; Location = 'Gate B North Matrix'; Weights = 'models/smoke_fire.pt'; Stream = '..\\videos\\Firing.mp4' },
        @{ CameraId = 'CAM-015'; Location = 'Parking Lot C Matrix'; Weights = 'models/weapon_best.pt'; Stream = '..\\videos\\smoke_fire.mp4' }
    )

    foreach ($cfg in $workerMatrix) {
        Write-Host "Starting worker $($cfg.CameraId) ($($cfg.Weights) on $($cfg.Stream)) ..."
        Start-Process powershell -ArgumentList @(
            '-NoExit',
            '-Command',
            "Set-Location '$backendPath'; & '$venvActivate'; python scripts/run_vision_worker.py --api-base-url http://localhost:8001/api/v1 --api-key $ingestionApiKey --mode yolo --yolo-weights $($cfg.Weights) --camera-id $($cfg.CameraId) --location '$($cfg.Location)' --stream-url $($cfg.Stream)"
        )
    }
}

Write-Host 'Started. Frontend: http://localhost:8000 | Backend: http://localhost:8001/docs'
