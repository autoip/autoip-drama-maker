#!/usr/bin/env bash
# One-line installer for autoip-mv-maker (macOS / Linux / Git Bash on Windows):
#   curl -fsSL https://raw.githubusercontent.com/jsleetw/autoip-mv-maker/main/install.sh | bash
# Env:
#   AUTOIP_MV_HOME       install dir (default ~/.autoip-mv-maker)
#   AUTOIP_MV_AGENTS     where to install skills: claude,codex (default) | claude | codex | none
#   AUTOIP_MV_SKIP_DEPS  1 = skip the Python venv / packages
#   AUTOIP_MV_REPO       git URL (default https://github.com/jsleetw/autoip-mv-maker.git)
set -euo pipefail

REPO="${AUTOIP_MV_REPO:-https://github.com/jsleetw/autoip-mv-maker.git}"
HOME_DIR="${AUTOIP_MV_HOME:-$HOME/.autoip-mv-maker}"
AGENTS="${AUTOIP_MV_AGENTS:-claude,codex}"
FACE_URL="https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"

say() { printf '\033[1;35m[autoip-mv-maker]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[autoip-mv-maker]\033[0m %s\n' "$*" >&2; }
need() { command -v "$1" >/dev/null 2>&1 || { warn "missing: $1 — $2"; exit 1; }; }

need git "install git first"

# 1. code
if [ -d "$HOME_DIR/.git" ]; then
  say "updating $HOME_DIR"
  git -C "$HOME_DIR" pull --ff-only --quiet
else
  say "cloning into $HOME_DIR"
  git clone --depth 1 --quiet "$REPO" "$HOME_DIR"
fi

# 2. python venv + packages
if [ "${AUTOIP_MV_SKIP_DEPS:-}" != "1" ]; then
  PYBIN=""
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
      PYBIN="$c"; break
    fi
  done
  [ -n "$PYBIN" ] || { warn "Python 3.10+ not found (set AUTOIP_MV_SKIP_DEPS=1 to skip)"; exit 1; }
  [ -d "$HOME_DIR/.venv" ] || { say "creating venv"; "$PYBIN" -m venv "$HOME_DIR/.venv"; }
  VPY="$HOME_DIR/.venv/bin/python"; [ -x "$VPY" ] || VPY="$HOME_DIR/.venv/Scripts/python.exe"
  say "installing Python packages (PyTorch for Demucs is large; this can take a while)"
  "$VPY" -m pip install --quiet --upgrade pip
  "$VPY" -m pip install --quiet -r "$HOME_DIR/requirements.txt"
fi

# 3. face model
if [ ! -f "$HOME_DIR/models/face_landmarker.task" ]; then
  say "downloading MediaPipe face model"
  curl -fsSL -o "$HOME_DIR/models/face_landmarker.task" "$FACE_URL" || warn "face model download failed; see docs/en/SETUP.md"
fi

# 4. skills
install_skills() {  # $1 = target skills dir
  mkdir -p "$1"
  for s in "$HOME_DIR"/skills/*/; do
    name="$(basename "$s")"; dst="$1/$name"
    if [ -e "$dst" ] && ! diff -rq "$s" "$dst" >/dev/null 2>&1; then
      rm -rf "$dst.bak"; mv "$dst" "$dst.bak"; warn "backed up existing $dst -> $dst.bak"
    fi
    rm -rf "$dst"; cp -R "$s" "$dst"
  done
  say "skills installed to $1"
}
case ",$AGENTS," in *,claude,*) install_skills "$HOME/.claude/skills" ;; esac
case ",$AGENTS," in *,codex,*)  install_skills "${CODEX_HOME:-$HOME/.codex}/skills" ;; esac

# 5. what's left
command -v ffmpeg >/dev/null 2>&1 || warn "ffmpeg not found — install one with libass (see docs/en/SETUP.md)"
[ -n "${AUTOIP_API_KEY:-}" ] || warn "AUTOIP_API_KEY is not set — get a key from your AutoIP dashboard and export it"
say "done. Fonts are not bundled: see $HOME_DIR/docs/en/SETUP.md"
say "In Claude Code or Codex, try: \"Use autoip-mv-maker to turn song.mp3 into a music video\""
