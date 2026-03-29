param(
    [switch]$WithWorkers
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendPath = Join-Path $repoRoot 'server'
$clientPath = Join-Path $repoRoot 'client'
$pythonExe = Join-Path $repoRoot '.venv\Scripts\python.exe'
$serverEnvPath = Join-Path $backendPath '.env'
$controlRoomConfigPath = Join-Path $repoRoot 'configs\control_room_cameras.json'

function Start-IntegratedJob {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $jobName = "ps5-$Name-$([guid]::NewGuid().ToString('N').Substring(0, 6))"
    $job = Start-Job -Name $jobName -ScriptBlock {
        param($wd, $file, $argsList)
        Set-Location $wd
        & $file @argsList
    } -ArgumentList $WorkingDirectory, $FilePath, $Arguments

    Write-Host "$Name started in VS Code job $($job.Id) ($jobName)"
}

function Get-ProfileHintFromText {
    param([string]$Text)

    $joined = ([string]$Text).ToLowerInvariant()
    if ($joined -match 'smoke|fire|hazard') {
        return 'fire-smoke'
    }
    if ($joined -match 'weapon|gun|knife|firing|firearm') {
        return 'weapon'
    }
    return 'generic'
}

function Get-SampleRateFromArgs {
    param([string]$Text)

    $defaultRate = 2
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return $defaultRate
    }

    $match = [regex]::Match($Text, '--sample-every-n-frames\s+(\d+)')
    if ($match.Success) {
        $parsed = 0
        if ([int]::TryParse($match.Groups[1].Value, [ref]$parsed) -and $parsed -gt 0) {
            return $parsed
        }
    }

    return $defaultRate
}

Write-Host 'Cleaning existing local dev processes ...'
& (Join-Path $PSScriptRoot 'dev-down.ps1')

# Remove stale local jobs from previous runs in this VS Code terminal session.
Get-Job -Name 'ps5-*' -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Job -Id $_.Id -Force -ErrorAction SilentlyContinue
    Remove-Job -Id $_.Id -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found at $pythonExe"
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

Write-Host 'Starting backend on http://localhost:8001 in current terminal session ...'
Start-IntegratedJob -Name 'Backend' -WorkingDirectory $backendPath -FilePath $pythonExe -Arguments @(
    '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8001'
)

Write-Host 'Starting frontend on http://localhost:8000 in current terminal session ...'
Start-IntegratedJob -Name 'Frontend' -WorkingDirectory $clientPath -FilePath 'npm.cmd' -Arguments @(
    'run', 'dev', '--', '--host', '0.0.0.0', '--port', '8000'
)

if ($WithWorkers) {
    if ([string]::IsNullOrWhiteSpace($ingestionApiKey)) {
        Write-Error 'INGESTION_API_KEY is empty in server/.env. Set it before starting workers.'
    }

    $weightsDir = Join-Path $backendPath 'models\weights'
    $firingModel = Get-ChildItem -Path $weightsDir -Filter 'firing*.pt' -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $firingModel) {
        Write-Error "No firing model found in $weightsDir"
    }

    $fireSmokeModel = Get-ChildItem -Path $weightsDir -Filter '*.pt' -File |
        Where-Object { $_.Name -match 'fire[_-]?smoke|smoke[_-]?fire' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $fireSmokeModel) {
        Write-Error "No fire/smoke model found in $weightsDir"
    }

    $workerMatrix = @()

    if (Test-Path $controlRoomConfigPath) {
        Write-Host "Loading control room worker config from $controlRoomConfigPath ..."
        $raw = Get-Content -Path $controlRoomConfigPath -Raw
        $config = ConvertFrom-Json -InputObject $raw

        foreach ($entry in $config) {
            $cameraId = [string]$entry.camera_id
            $location = [string]$entry.location
            $stream = [string]$entry.stream_url
            $profile = [string]$entry.profile
            $weights = [string]$entry.weights
            $extraArgs = [string]$entry.extra_args

            if ([string]::IsNullOrWhiteSpace($cameraId) -or [string]::IsNullOrWhiteSpace($stream)) {
                Write-Host 'Skipping invalid control room camera entry (missing camera_id or stream_url).'
                continue
            }

            if ([string]::IsNullOrWhiteSpace($location)) {
                $location = $cameraId
            }

            if ([string]::IsNullOrWhiteSpace($profile)) {
                $profile = Get-ProfileHintFromText -Text "$cameraId $location $stream $extraArgs $weights"
            }

            if ([string]::IsNullOrWhiteSpace($weights)) {
                if ($profile -eq 'fire-smoke') {
                    $weights = "models/weights/$($fireSmokeModel.Name)"
                } else {
                    $weights = "models/weights/$($firingModel.Name)"
                }
            }

            $workerMatrix += [pscustomobject]@{
                CameraId = $cameraId
                Location = $location
                Weights = $weights
                Stream = $stream
                SampleEveryNFrames = Get-SampleRateFromArgs -Text $extraArgs
            }
        }
    }

    if ($workerMatrix.Count -eq 0) {
        # Keep default local workload light to reduce lag in the dashboard.
        $workerMatrix = @(
            [pscustomobject]@{
                CameraId = 'CAM-012';
                Location = 'Gate B North';
                Weights = "models/weights/$($firingModel.Name)";
                Stream = '..\\videos\\Firing.mp4';
                SampleEveryNFrames = 2
            },
            [pscustomobject]@{
                CameraId = 'CAM-013';
                Location = 'Parking Lot C';
                Weights = "models/weights/$($fireSmokeModel.Name)";
                Stream = '..\\videos\\smoke_fire.mp4';
                SampleEveryNFrames = 2
            }
        )
    }

    $generatedConfigDir = Join-Path $repoRoot 'runs\detect\multi_camera_configs'
    New-Item -ItemType Directory -Path $generatedConfigDir -Force | Out-Null

    $workerGroups = $workerMatrix | Group-Object Weights
    $workerIndex = 0

    foreach ($group in $workerGroups) {
        $workerIndex += 1
        $weights = [string]$group.Name
        $safeWeightName = [System.IO.Path]::GetFileNameWithoutExtension($weights)
        if ([string]::IsNullOrWhiteSpace($safeWeightName)) {
            $safeWeightName = "worker$workerIndex"
        }

        $cameraPayload = @()
        foreach ($cfg in $group.Group) {
            $cameraPayload += [ordered]@{
                camera_id = [string]$cfg.CameraId
                location = [string]$cfg.Location
                stream_url = [string]$cfg.Stream
                sample_every_n_frames = [int]$cfg.SampleEveryNFrames
            }
        }

        $groupConfigPath = Join-Path $generatedConfigDir ("multi_worker_{0}_{1}.json" -f $workerIndex, $safeWeightName)
        $jsonPayload = ConvertTo-Json -InputObject @($cameraPayload) -Depth 6
        Set-Content -Path $groupConfigPath -Encoding UTF8 -Value $jsonPayload

        Write-Host "Starting grouped worker $safeWeightName with $($cameraPayload.Count) camera(s) using $weights ..."

        $workerArgs = @(
            'scripts/run_multi_camera_worker.py',
            '--config', $groupConfigPath,
            '--api-base-url', 'http://localhost:8001/api/v1',
            '--api-key', $ingestionApiKey,
            '--mode', 'yolo',
            '--weights', $weights
        )

        Start-IntegratedJob -Name "Worker-$safeWeightName" -WorkingDirectory $backendPath -FilePath $pythonExe -Arguments $workerArgs
    }
}

Write-Host 'Started. Frontend: http://localhost:8000 | Backend: http://localhost:8001/docs'
