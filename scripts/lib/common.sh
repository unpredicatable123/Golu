#!/usr/bin/env bash
# Shared helpers for render_all.sh / encode_frames.sh (Git Bash on Windows, bash on macOS/Linux).

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT/renders/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_FILE:-$LOG_DIR/$(date +%Y%m%d).log}"

log() {
  local msg="[$(date +%H:%M:%S)] $*"
  echo "$msg" >&2
  echo "$msg" >> "$LOG_FILE"
}

die() {
  log "ERROR: $*"
  exit 1
}

# Locate Blender: $BLENDER → PATH → standard install locations. Prints the path.
find_blender() {
  if [[ -n "${BLENDER:-}" && -x "$BLENDER" ]]; then echo "$BLENDER"; return 0; fi
  if command -v blender >/dev/null 2>&1; then command -v blender; return 0; fi
  local c
  for c in /d/Tools/blender-4.5*/blender.exe \
           "/c/Program Files/Blender Foundation"/Blender*/blender.exe \
           "$LOCALAPPDATA/Programs/Blender Foundation"/Blender*/blender.exe \
           /Applications/Blender.app/Contents/MacOS/Blender \
           /usr/bin/blender /usr/local/bin/blender /snap/bin/blender; do
    if [[ -x "$c" ]]; then echo "$c"; return 0; fi
  done
  return 1
}

# Succeeds when the Blender version is 4.2 or newer.
blender_version_ok() {
  local ver major minor
  ver="$("$1" -b --factory-startup --version 2>/dev/null | grep -m1 -oE 'Blender [0-9]+\.[0-9]+' | cut -d' ' -f2)"
  [[ -z "$ver" ]] && return 1
  major="${ver%%.*}"; minor="${ver#*.}"
  (( major > 4 || (major == 4 && minor >= 2) ))
}

# run_blender <script.py> [args after --]
run_blender() {
  local script="$1"; shift
  "$BLENDER" -b --factory-startup --python-exit-code 1 -P "$ROOT/$script" -- "$@"
}

require_blender() {
  BLENDER="$(find_blender)" || die "Blender not found. Install Blender 4.5 LTS and set BLENDER=/path/to/blender"
  blender_version_ok "$BLENDER" || die "Blender at $BLENDER is older than 4.2"
  export BLENDER
  log "using Blender: $BLENDER"
}

require_ffmpeg() {
  command -v ffmpeg >/dev/null 2>&1 || die "ffmpeg not found on PATH"
  ffmpeg -hide_banner -encoders 2>/dev/null | grep -q libwebp || die "ffmpeg lacks the libwebp encoder"
}
