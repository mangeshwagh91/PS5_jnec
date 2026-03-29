@echo off
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "CAMERA_CONFIG=%ROOT%server\scripts\cameras.json"
set "CAMERA_CONFIG_PATH=%CAMERA_CONFIG%"
set "API_BASE_URL=http://localhost:8001/api/v1"
set "DEVICE=0"

if not exist "%PY%" (
  echo [ERROR] Python virtual environment not found at %PY%
  echo Create it first, then rerun this file.
  pause
  exit /b 1
)

if not exist "%CAMERA_CONFIG%" (
  echo [ERROR] Camera config not found at %CAMERA_CONFIG%
  pause
  exit /b 1
)

set "INGESTION_API_KEY="
if exist "%ROOT%server\.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%server\.env") do (
    if /I "%%A"=="INGESTION_API_KEY" set "INGESTION_API_KEY=%%B"
  )
)

if "%INGESTION_API_KEY%"=="" (
  echo [WARN] INGESTION_API_KEY was not found. Events may be rejected if backend auth is enabled.
)

echo Starting backend API on port 8001...
start "School Backend" cmd /k "set CAMERA_CONFIG_PATH=%CAMERA_CONFIG_PATH%&& cd /d ""%ROOT%server""&& ""%PY%"" -m uvicorn app.main:app --host 0.0.0.0 --port 8001"

timeout /t 2 >nul

echo Starting unified school worker (fire + smoke + weapon per camera)...
start "School Worker" cmd /k "cd /d ""%ROOT%server""&& ""%PY%"" scripts\run_school_surveillance.py --config scripts\cameras.json --mode yolo --fire-weights models\weights\fire_smoke_2.pt --weapon-weights models\weights\firing_1.pt --device %DEVICE% --api-base-url %API_BASE_URL% --api-key %INGESTION_API_KEY%"

if exist "%ROOT%client" (
  timeout /t 2 >nul
  echo Starting frontend dashboard on port 8000...
  where bun >nul 2>nul
  if %ERRORLEVEL% EQU 0 (
    start "School Frontend" cmd /k "cd /d ""%ROOT%client""&& bun run dev --host 0.0.0.0 --port 8000"
  ) else (
    start "School Frontend" cmd /k "cd /d ""%ROOT%client""&& npm run dev -- --host 0.0.0.0 --port 8000"
  )
)

timeout /t 2 >nul
start "" "http://localhost:8000"

where ngrok >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  echo Starting ngrok tunnel for judges...
  start "School ngrok" cmd /k "ngrok http 8000"
) else (
  echo [INFO] ngrok not found in PATH. Install ngrok and run: ngrok http 8000
)

echo.
echo Presentation stack launched.
echo Frontend: http://localhost:8000
echo Backend docs: http://localhost:8001/docs
echo.
echo Edit server\scripts\cameras.json anytime to change cameras/videos.

pause
endlocal
