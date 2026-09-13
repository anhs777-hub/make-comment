# make-comment 상태 확인 (Windows 전용, 상시 실행 사용자용 — docs/always-on.md 참고)
# 이 파일 위치 기준 상대 경로로 동작한다. 어디에 폴더를 두어도 그대로 쓸 수 있다.

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$rootName = Split-Path -Leaf $root
$logPath = Join-Path $root "logs\bot.log"
$mainPath = Join-Path $root "scripts\main.py"

Clear-Host
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   make-comment - Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Folder: $root"
Write-Host ""

# 실행 중인 프로세스 확인 (이 폴더의 main.py만)
$process = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like "*$rootName*main.py*" }
if ($process) {
    Write-Host "[O] Running (PID: $($process.ProcessId))" -ForegroundColor Green
} else {
    Write-Host "[X] Not Running" -ForegroundColor Red
    Write-Host "    (main.py is a run-once program; this is normal outside a scheduled run)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "Recent Logs:" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Gray

if (Test-Path $logPath) {
    Get-Content $logPath -Tail 15 -Encoding UTF8
} else {
    Write-Host "(No logs yet)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "[1] Live Logs  [2] Run Once (dry-run)  [3] Stop  [4] Exit" -ForegroundColor Magenta
Write-Host "----------------------------------------" -ForegroundColor Gray
$choice = Read-Host "Select"

switch ($choice) {
    "1" {
        if (Test-Path $logPath) {
            Write-Host "Live logs (Ctrl+C to exit):" -ForegroundColor Yellow
            Get-Content $logPath -Tail 20 -Wait -Encoding UTF8
        } else {
            Write-Host "(No logs yet)" -ForegroundColor Gray
        }
    }
    "2" {
        $venvPython = Join-Path $root ".venv\Scripts\python.exe"
        if (-not (Test-Path $venvPython)) { $venvPython = "python" }
        Write-Host "Running once (dry-run)..." -ForegroundColor Yellow
        & $venvPython $mainPath --dry-run
    }
    "3" {
        $proc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -like "*$rootName*main.py*" }
        if ($proc) {
            Stop-Process -Id $proc.ProcessId -Force
            Write-Host "Stopped!" -ForegroundColor Green
        } else {
            Write-Host "Nothing to stop." -ForegroundColor Gray
        }
        Start-Sleep -Seconds 2
    }
    "4" { exit }
}
