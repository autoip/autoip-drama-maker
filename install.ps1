# One-line installer for autoip-mv-maker (Windows PowerShell):
#   irm https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.ps1 | iex
# Env:
#   AUTOIP_MV_HOME       install dir (default ~\.autoip-mv-maker)
#   AUTOIP_MV_AGENTS     where to install skills: claude,codex (default) | claude | codex | none
#   AUTOIP_MV_SKIP_DEPS  1 = skip the Python venv / packages
#   AUTOIP_MV_REPO       git URL (default https://github.com/jsleetw/autoip-mv-maker.git)
& {
$ErrorActionPreference = 'Stop'
$Repo    = if ($env:AUTOIP_MV_REPO)   { $env:AUTOIP_MV_REPO }   else { 'https://github.com/jsleetw/autoip-mv-maker.git' }
$HomeDir = if ($env:AUTOIP_MV_HOME)   { $env:AUTOIP_MV_HOME }   else { Join-Path $HOME '.autoip-mv-maker' }
$Agents  = if ($env:AUTOIP_MV_AGENTS) { $env:AUTOIP_MV_AGENTS } else { 'claude,codex' }
$Agents  = $Agents -split ','
$FaceUrl = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task'

function Say($m)  { Write-Host "[autoip-mv-maker] $m" -ForegroundColor Magenta }
function Warn($m) { Write-Host "[autoip-mv-maker] $m" -ForegroundColor Yellow }
function Native { & $args[0] @($args | Select-Object -Skip 1); if ($LASTEXITCODE) { throw "failed: $($args -join ' ')" } }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'missing: git (winget install Git.Git)' }

# 1. code
if (Test-Path (Join-Path $HomeDir '.git')) {
    Say "updating $HomeDir"
    Native git -C $HomeDir pull --ff-only --quiet
} else {
    Say "cloning into $HomeDir"
    Native git clone --depth 1 --quiet $Repo $HomeDir
}

# 2. python venv + packages
if ($env:AUTOIP_MV_SKIP_DEPS -ne '1') {
    $Py = $null
    foreach ($c in 'python', 'python3', 'py') {
        if (Get-Command $c -ErrorAction SilentlyContinue) {
            & $c -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>$null
            if ($LASTEXITCODE -eq 0) { $Py = $c; break }
        }
    }
    if (-not $Py) { throw 'Python 3.10+ not found (winget install Python.Python.3.13, or set AUTOIP_MV_SKIP_DEPS=1)' }
    $Venv = Join-Path $HomeDir '.venv'
    if (-not (Test-Path $Venv)) { Say 'creating venv'; Native $Py -m venv $Venv }
    $VPy = Join-Path $Venv 'Scripts\python.exe'
    Say 'installing Python packages (PyTorch for Demucs is large; this can take a while)'
    Native $VPy -m pip install --quiet --upgrade pip
    Native $VPy -m pip install --quiet -r (Join-Path $HomeDir 'requirements.txt')
}

# 3. face model
$Face = Join-Path $HomeDir 'models\face_landmarker.task'
if (-not (Test-Path $Face)) {
    Say 'downloading MediaPipe face model'
    try { Invoke-WebRequest -UseBasicParsing -Uri $FaceUrl -OutFile $Face } catch { Warn 'face model download failed; see docs/en/SETUP.md' }
}

# 4. skills
function Install-Skills($Target) {
    New-Item -ItemType Directory -Force $Target | Out-Null
    foreach ($s in Get-ChildItem -Directory (Join-Path $HomeDir 'skills')) {
        $dst = Join-Path $Target $s.Name
        if (Test-Path $dst) {
            $a = Get-ChildItem -Recurse -File $s.FullName | ForEach-Object { (Get-FileHash $_.FullName).Hash }
            $b = Get-ChildItem -Recurse -File $dst | ForEach-Object { (Get-FileHash $_.FullName).Hash }
            if (Compare-Object @($a) @($b)) {
                if (Test-Path "$dst.bak") { Remove-Item -Recurse -Force "$dst.bak" }
                Move-Item $dst "$dst.bak"; Warn "backed up existing $dst -> $dst.bak"
            } else { Remove-Item -Recurse -Force $dst }
        }
        Copy-Item -Recurse $s.FullName $dst
    }
    Say "skills installed to $Target"
}
if ($Agents -contains 'claude') { Install-Skills (Join-Path $HOME '.claude\skills') }
if ($Agents -contains 'codex') {
    $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    Install-Skills (Join-Path $CodexHome 'skills')
}

# 5. what's left
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { Warn 'ffmpeg not found - winget install Gyan.FFmpeg' }
if (-not $env:AUTOIP_API_KEY) { Warn 'AUTOIP_API_KEY is not set - get a key from your AutoIP dashboard, then: $env:AUTOIP_API_KEY = "aip_..."' }
Say "done. Fonts are not bundled: see $HomeDir\docs\en\SETUP.md"
Say 'In Claude Code or Codex, try: "Use autoip-mv-maker to turn song.mp3 into a music video"'
}
