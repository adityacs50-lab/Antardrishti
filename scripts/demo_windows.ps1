# prahari — Windows one-command demo (SIH26165)
#
# Prefer Python 3.11 (py -3.11). Falls back to `python` if 3.11 is missing.
# Usage (from repo root or anywhere):
#   powershell -ExecutionPolicy Bypass -File .\scripts\demo_windows.ps1
#
# Flags:
#   -SkipSeed   skip corpus seed if DB already populated
#   -Dev        use Vite hot reload instead of serving web/dist
#   -SeedLimit  number of reports to seed (default 700)

param(
    [switch]$SkipSeed,
    [switch]$Dev,
    [int]$SeedLimit = 700,
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Repo

function Find-Python {
    $candidates = @("py -3.11", "py -3.12", "python")
    foreach ($c in $candidates) {
        try {
            if ($c -like "py *") {
                $parts = $c.Split(" ")
                $ver = & $parts[0] $parts[1] -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) {
                    return @{ Launcher = $parts[0]; Args = @($parts[1]); Version = $ver.Trim() }
                }
            } else {
                $ver = & $c -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
                if ($LASTEXITCODE -eq 0 -and $ver) {
                    return @{ Launcher = $c; Args = @(); Version = $ver.Trim() }
                }
            }
        } catch { }
    }
    throw "No suitable Python found. Install Python 3.11+ and retry."
}

$Py = Find-Python
Write-Host ""
Write-Host "  prahari Windows demo" -ForegroundColor Cyan
Write-Host "  Python $($Py.Version) via $($Py.Launcher) $($Py.Args -join ' ')"
Write-Host "  Repo: $Repo"
Write-Host ""

# OneDrive / Desktop SQLite tip — keep the DB under LocalAppData; keep corpus
# in the repo (PRAHARI_CORPUS_PATH). Do not redirect PRAHARI_DATA_DIR away from
# the repo or seed will look for synthetic_reports.jsonl in the wrong place.
if (-not $env:PRAHARI_DB_PATH) {
    $localData = Join-Path $env:LOCALAPPDATA "prahari"
    New-Item -ItemType Directory -Force -Path $localData | Out-Null
    $env:PRAHARI_DB_PATH = Join-Path $localData "prahari.db"
    Write-Host "  PRAHARI_DB_PATH -> $($env:PRAHARI_DB_PATH) (avoids OneDrive Desktop SQLite issues)"
}
$corpusDefault = Join-Path $Repo "data\synthetic_reports.jsonl"
if (-not $env:PRAHARI_CORPUS_PATH) {
    $env:PRAHARI_CORPUS_PATH = $corpusDefault
}

function Invoke-Py {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$PyArgs)
    if ($Py.Args.Count -gt 0) {
        & $Py.Launcher @($Py.Args + $PyArgs)
    } else {
        & $Py.Launcher @PyArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "Python command failed: $($PyArgs -join ' ')" }
}

Write-Host "  Ensuring package is installed..."
Invoke-Py -m pip install -e ".[dev]" -q

Write-Host "  Migrating / creating tables..."
# create_all on startup; seed uses the CLI
if (-not $SkipSeed) {
    Write-Host "  Seeding $SeedLimit reports (deterministic seed=42)..."
    $env:PYTHONPATH = Join-Path $Repo "backend"
    Invoke-Py -m prahari.cli seed --limit $SeedLimit
}

if (-not $Dev) {
    Write-Host "  Building frontend..."
    Push-Location (Join-Path $Repo "web")
    if (-not (Test-Path "node_modules")) { npm ci }
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "Frontend build failed" }
    Pop-Location
}

# Free ports if stale processes linger
foreach ($port in @($ApiPort, $WebPort)) {
    $owners = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $owners) {
        if ($procId -and $procId -ne 0) {
            Write-Host "  Stopping PID $procId on port $port"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}

$env:PYTHONPATH = Join-Path $Repo "backend"
$apiProc = Start-Process -PassThru -WindowStyle Minimized -FilePath $Py.Launcher -ArgumentList (
    @($Py.Args) + @(
        "-m", "uvicorn", "prahari.main:app",
        "--host", "127.0.0.1", "--port", "$ApiPort", "--log-level", "warning"
    )
)

Write-Host "  Waiting for API on :$ApiPort ..."
$healthy = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$ApiPort/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $healthy = $true; break }
    } catch { Start-Sleep -Milliseconds 500 }
}
if (-not $healthy) {
    Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue
    throw "API failed to start. Check PRAHARI_DATA_DIR and Python version."
}

$webProc = $null
if ($Dev) {
    $webProc = Start-Process -PassThru -WindowStyle Minimized -FilePath "npm" -ArgumentList @(
        "run", "dev", "--", "--host", "127.0.0.1", "--port", "$WebPort"
    ) -WorkingDirectory (Join-Path $Repo "web")
    $uiUrl = "http://localhost:$WebPort"
} else {
    # Prefer FastAPI serving web/dist (SPA mount). Also expose Vite-less UI on :5173
    # via Python SPA static server matching launch_demo.sh behavior for judges.
    $spaScript = @"
import http.server, os, socketserver, sys
PORT = int(sys.argv[1])
os.chdir(r'$(Join-Path $Repo "web\dist")')
class SPA(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        target = path.lstrip('/')
        if target and os.path.exists(target) and not os.path.isdir(target):
            return super().do_GET()
        self.path = '/index.html'
        return super().do_GET()
    def log_message(self, *args):
        pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(('127.0.0.1', PORT), SPA) as httpd:
    httpd.serve_forever()
"@
    $spaFile = Join-Path $env:TEMP "prahari_spa_server.py"
    Set-Content -Path $spaFile -Value $spaScript -Encoding UTF8
    $webProc = Start-Process -PassThru -WindowStyle Minimized -FilePath $Py.Launcher -ArgumentList (
        @($Py.Args) + @($spaFile, "$WebPort")
    )
    $uiUrl = "http://localhost:$WebPort"
}

Start-Sleep -Seconds 2
Start-Process $uiUrl

Write-Host ""
Write-Host ("  " + ("=" * 64)) -ForegroundColor Green
Write-Host "  UI    $uiUrl"
Write-Host "  API   http://localhost:$ApiPort/docs"
Write-Host "  Also  http://localhost:$ApiPort/  (SPA via FastAPI if dist built)"
Write-Host ("  " + ("=" * 64)) -ForegroundColor Green
Write-Host "  Runbook: DEMO.md   Judges: JUDGES.md"
Write-Host "  Press Ctrl+C in this window to stop, or close it after the demo."
Write-Host ""

try {
    Wait-Process -Id $apiProc.Id
} finally {
    if ($webProc -and -not $webProc.HasExited) { Stop-Process -Id $webProc.Id -Force -ErrorAction SilentlyContinue }
    if ($apiProc -and -not $apiProc.HasExited) { Stop-Process -Id $apiProc.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "  Stopped."
}
