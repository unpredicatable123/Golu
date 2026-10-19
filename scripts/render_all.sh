#!/usr/bin/env bash
# Render orchestration (SPEC §4.8).
#   scripts/render_all.sh --quality draft|high|final [--steps 1-9] [--doors] [--props] [--qa] [--all]
#                         [--yes] [--stride N] [--blender PATH]
# Draft: 960x540 EEVEE. High: 1920x1080 EEVEE 16 spl (D58; use --stride 2 + encode --interpolate, D59).
# Final: 1920x1080 Cycles 96 spp + OIDN. Resumable: finished frames are skipped.
# High and final renders first measure probe frames, print the total estimate and wait for confirmation.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

QUALITY=""
STEPS="1-9"
DO_STEPS=1
DO_DOORS=0
DO_PROPS=0
DO_QA=0
YES=0
STRIDE=1

usage() {
  sed -n '2,7p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quality) QUALITY="$2"; shift 2 ;;
      --steps) STEPS="$2"; shift 2 ;;
      --doors) DO_DOORS=1; shift ;;
      --props) DO_PROPS=1; shift ;;
      --qa) DO_QA=1; shift ;;
      --all) DO_DOORS=1; DO_PROPS=1; shift ;;
      --only-extras) DO_STEPS=0; shift ;;
      --yes|-y) YES=1; shift ;;
      --stride) STRIDE="$2"; shift 2 ;;
      --blender) BLENDER="$2"; shift 2 ;;
      -h|--help) usage 0 ;;
      *) echo "unknown option: $1" >&2; usage 1 ;;
    esac
  done
  [[ "$QUALITY" =~ ^(draft|high|final)$ ]] || { echo "--quality draft|high|final is required" >&2; usage 1; }
  if [[ "$QUALITY" == "final" && "$STRIDE" != "1" ]]; then die "--stride is for draft previews and the high tier (D59)"; fi
}

count_steps_frames() {
  # frames to render for the selected steps, from the manifest (falls back to the spec layout)
  local manifest="$ROOT/renders/manifest.json"
  node -e '
    const fs=require("fs"); const [m, spec]=[process.argv[1], process.argv[2]];
    const sel=new Set(); for (const part of spec.split(",")) { const [a,b]=part.split("-").map(Number);
      for (let i=a;i<=(b||a);i++) sel.add(i); }
    let n=0;
    if (fs.existsSync(m)) { for (const s of JSON.parse(fs.readFileSync(m,"utf8")).steps) if (sel.has(s.id)) n+=s.count; }
    else { for (const i of sel) n += i<9 ? 120 : 168; }
    console.log(n);' "$manifest" "$STEPS"
}

estimate_and_confirm() {
  log "measuring probe frames at $QUALITY quality…"
  local spf
  spf="$(run_blender blender/render_steps.py --quality "$QUALITY" --probe | grep -oE 'seconds_per_frame=[0-9.]+' | cut -d= -f2)"
  [[ -n "$spf" ]] || die "probe failed"
  local frames extra total_s
  frames=$(( $(count_steps_frames) / STRIDE ))
  extra=0
  (( DO_DOORS )) && extra=$(( extra + 72 / STRIDE ))
  total_s="$(node -e "const s=$spf,f=$frames,d=$extra; const t=(f*s + d*s*1.4 + (${DO_PROPS}?12*s*1.2:0))*1.10; console.log(Math.round(t))")"
  local h=$(( total_s / 3600 )) m=$(( (total_s % 3600) / 60 ))
  echo
  echo "================ FINAL RENDER ESTIMATE ================"
  echo "  measured: ${spf} s/frame ($QUALITY, 1920x1080)"
  echo "  fly-through frames: ${frames}   door frames: ${extra}   sprites: $(( DO_PROPS * 12 ))"
  echo "  estimated total: ${h} h ${m} min (+10% load/IO)"
  echo "======================================================="
  if (( ! YES )); then
    read -r -p "Proceed with the final render? [y/N] " ans
    [[ "$ans" =~ ^[Yy]$ ]] || die "final render cancelled"
  fi
}

main() {
  parse_args "$@"
  require_blender
  local stride_args=()
  [[ "$STRIDE" != "1" ]] && stride_args=(--stride "$STRIDE")
  log "building scene ($QUALITY)…"
  local scene_q="$QUALITY"; [[ "$QUALITY" == "high" ]] && scene_q="draft"     # high renders the draft scene
  run_blender blender/build_scene.py --quality "$scene_q" --verify
  if [[ "$QUALITY" != "draft" ]]; then estimate_and_confirm; fi
  if (( DO_QA )); then
    log "QA turntables…"
    run_blender blender/render_qa.py --quality "$QUALITY" --sweep
  fi
  if (( DO_STEPS )); then
    log "rendering steps $STEPS…"
    run_blender blender/render_steps.py --quality "$QUALITY" --steps "$STEPS" "${stride_args[@]}"
  fi
  if (( DO_DOORS )); then
    log "rendering doors…"
    run_blender blender/render_doors.py --quality "$QUALITY" "${stride_args[@]}"
  fi
  if (( DO_PROPS )); then
    log "rendering prop sprites…"
    run_blender blender/render_props.py --quality "$QUALITY" --verify
  fi
  log "render_all complete"
}

main "$@"
