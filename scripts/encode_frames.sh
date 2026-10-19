#!/usr/bin/env bash
# PNG → WebP (desktop 1920w q85, mobile 960w q78, light unsharp), door video + posters, prop sprites, frames.json (SPEC §4.8).
#   scripts/encode_frames.sh --quality draft|high|final [--steps 1-9] [--force] [--fill-gaps] [--interpolate]
# --fill-gaps (draft previews only) holds the nearest rendered frame for every missing one, e.g. after --stride.
# --interpolate rebuilds the even frames of a --stride 2 render with motion-compensated interpolation (D59).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

QUALITY=""
STEPS="1-9"
FORCE=0
FILL_GAPS=0
INTERP=0
NO_DOORS=0
STATIC="$ROOT/web/static"

usage() { sed -n '2,3p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --quality) QUALITY="$2"; shift 2 ;;
      --steps) STEPS="$2"; shift 2 ;;
      --force) FORCE=1; shift ;;
      --fill-gaps) FILL_GAPS=1; shift ;;
      --interpolate) INTERP=1; shift ;;
      --no-doors) NO_DOORS=1; shift ;;
      -h|--help) usage 0 ;;
      *) echo "unknown option: $1" >&2; usage 1 ;;
    esac
  done
  [[ "$QUALITY" =~ ^(draft|high|final)$ ]] || { echo "--quality draft|high|final is required" >&2; usage 1; }
  if [[ "$QUALITY" == "final" && "$FILL_GAPS" == 1 ]]; then die "--fill-gaps is a draft-only preview aid"; fi
}

# expected frame count for a step from the manifest
step_count() {
  node -e 'const m=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));
    console.log(m.steps[Number(process.argv[2])-1].count)' "$ROOT/renders/manifest.json" "$1"
}

expand_steps() {
  local out=() part a b i
  IFS=',' read -ra parts <<< "$STEPS"
  for part in "${parts[@]}"; do
    if [[ "$part" == *-* ]]; then a="${part%-*}"; b="${part#*-}"; for ((i=a; i<=b; i++)); do out+=("$i"); done
    else out+=("$part"); fi
  done
  echo "${out[@]}"
}

png_count() { find "$1" -maxdepth 1 -name 'f_*.png' 2>/dev/null | wc -l | tr -d ' '; }
webp_count() { find "$1" -maxdepth 1 -name 'f_*.webp' 2>/dev/null | wc -l | tr -d ' '; }

# frame_list <src_dir> <count> <list_file>: ffmpeg concat list f_0001..f_<count>; prints the number of gaps.
# A missing frame repeats the nearest earlier one (or the first rendered one before any exists).
frame_list() {
  local src="$1" count="$2" list="$3" i name last="" gaps=0 first ndir
  ndir="$(to_native "$src")"
  first="$(cd "$src" && ls f_*.png | sort | head -1)"
  : > "$list"
  for ((i = 1; i <= count; i++)); do
    printf -v name 'f_%04d.png' "$i"
    if [[ -f "$src/$name" ]]; then last="$name"; else gaps=$((gaps + 1)); name="${last:-$first}"; fi
    printf "file '%s/%s'\nduration 0.0416667\n" "$ndir" "$name" >> "$list"
  done
  echo "$gaps"
}

# encode_seq <src_dir> <dst_dir> <width> <quality> <count>
encode_seq() {
  local src="$1" dst="$2" w="$3" q="$4" count="$5"
  local n_src n_dst list gaps
  n_src="$(png_count "$src")"
  [[ "$n_src" -gt 0 ]] || die "no PNG frames in $src"
  mkdir -p "$dst"
  n_dst="$(webp_count "$dst")"
  if (( ! FORCE )) && [[ "$n_dst" == "$count" && -f "$dst/f_0001.webp" ]] \
     && [[ -z "$(find "$src" -maxdepth 1 -name 'f_*.png' -newer "$dst/f_0001.webp" | head -1)" ]]; then
    log "skip ${dst#$ROOT/} ($n_dst frames up to date)"; return 0
  fi
  list="$(mktemp)"
  gaps="$(frame_list "$src" "$count" "$list")"
  if (( gaps > 0 && ! FILL_GAPS )); then
    rm -f "$list"; die "${src#$ROOT/}: $gaps of $count frames missing (render them, or pass --fill-gaps for a draft preview)"
  fi
  rm -f "$dst"/f_*.webp
  # never upscale: draft frames are 960 px wide
  ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list" \
    -vf "scale='min(${w},iw)':-2:flags=lanczos,unsharp=5:5:0.7:5:5:0.0" -c:v libwebp -quality "$q" -compression_level 6 -preset picture \
    -fps_mode cfr -r 24 -start_number 1 -frames:v "$count" "$dst/f_%04d.webp"
  rm -f "$list"
  local held=""
  (( gaps > 0 )) && held=", $gaps held"
  log "encoded $(webp_count "$dst") frames → ${dst#$ROOT/} (≤${w}w q${q}${held})"
}

# interpolate_seq <list_file> <out_dir> <count>: the list holds the odd frames (1, 3, 5, …) of a sequence at
# 12 fps; motion-compensated interpolation to 24 fps restores every frame as out_dir/g_00001.png … g_<count>.
interpolate_seq() {
  local list="$1" out="$2" count="$3"
  rm -rf "$out"; mkdir -p "$out"
  ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$list"     -vf "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:me=epzs:search_param=96:vsbmc=1:scd=none"     -fps_mode cfr -frames:v "$count" -start_number 1 "$out/g_%05d.png"
  local got; got="$(find "$out" -name 'g_*.png' | wc -l | tr -d ' ')"
  # the last (even) frame lies past the final rendered one: hold it
  local i
  for ((i = got + 1; i <= count; i++)); do cp "$(printf '%s/g_%05d.png' "$out" "$got")" "$(printf '%s/g_%05d.png' "$out" "$i")"; done
}

# odd global frames across all steps (the camera move is continuous across steps) → renders/<q>/interp/stepN/
interpolate_steps() {
  local src_root="$ROOT/renders/$QUALITY/steps" dst_root="$ROOT/renders/$QUALITY/interp" list n count start local_i g f
  local total; total="$(node -e 'console.log(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8")).total)' "$ROOT/renders/manifest.json")"
  local have; have="$( (find "$dst_root" -path '*/step*/f_*.png' 2>/dev/null || true) | wc -l | tr -d ' ')"
  if (( ! FORCE )) && [[ "$have" == "$total" ]]      && [[ -z "$(find "$src_root" -name 'f_*.png' -newer "$dst_root/step9/f_0001.png" | head -1)" ]]; then
    log "skip interpolation (${dst_root#$ROOT/} up to date)"; return 0
  fi
  list="$(mktemp)"; : > "$list"
  for n in 1 2 3 4 5 6 7 8 9; do
    count="$(step_count "$n")"
    for ((local_i = 1; local_i <= count; local_i += 2)); do
      f="$(printf '%s/step%d/f_%04d.png' "$src_root" "$n" "$local_i")"
      [[ -f "$f" ]] || die "missing ${f#$ROOT/} (render with --stride 2 first)"
      printf "file '%s'\nduration 0.0833333\n" "$(to_native "$f")" >> "$list"
    done
  done
  log "interpolating $total frames from $(grep -c '^file' "$list") rendered (motion-compensated)…"
  interpolate_seq "$list" "$dst_root/_all" "$total"
  rm -f "$list"
  start=0
  for n in 1 2 3 4 5 6 7 8 9; do
    count="$(step_count "$n")"
    rm -rf "$dst_root/step$n"; mkdir -p "$dst_root/step$n"
    for ((local_i = 1; local_i <= count; local_i++)); do
      g=$((start + local_i))
      mv "$(printf '%s/_all/g_%05d.png' "$dst_root" "$g")" "$(printf '%s/step%d/f_%04d.png' "$dst_root" "$n" "$local_i")"
    done
    cp -f "$src_root/step$n"/f_*.png "$dst_root/step$n/"     # every real render beats an interpolated frame
    start=$((start + count))
  done
  rm -rf "$dst_root/_all"
  log "interpolated frames → ${dst_root#$ROOT/}"
}

encode_steps() {
  local src_root="$ROOT/renders/$QUALITY/steps" n
  (( INTERP )) && src_root="$ROOT/renders/$QUALITY/interp"
  local pids=()
  for n in $(expand_steps); do
    local count; count="$(step_count "$n")"
    ( encode_seq "$src_root/step$n" "$STATIC/frames/step$n" 1920 85 "$count"
      encode_seq "$src_root/step$n" "$STATIC/frames-mobile/step$n" 960 78 "$count" ) &
    pids+=($!)
    if (( ${#pids[@]} >= 4 )); then wait "${pids[0]}"; pids=("${pids[@]:1}"); fi
  done
  for p in "${pids[@]}"; do wait "$p"; done
}

encode_doors() {
  local src="$ROOT/renders/$QUALITY/doors"
  [[ -d "$src" ]] || { log "no door renders yet (skipping doors)"; return 0; }
  local n_doors=72
  if (( INTERP )); then
    local list i f; list="$(mktemp)"; : > "$list"
    for ((i = 1; i <= n_doors; i += 2)); do
      f="$(printf '%s/f_%04d.png' "$src" "$i")"
      [[ -f "$f" ]] || die "missing ${f#$ROOT/}"
      printf "file '%s'\nduration 0.0833333\n" "$(to_native "$f")" >> "$list"
    done
    interpolate_seq "$list" "$ROOT/renders/$QUALITY/interp/doors" "$n_doors"
    rm -f "$list"
    for ((i = 1; i <= n_doors; i++)); do
      mv "$(printf '%s/g_%05d.png' "$ROOT/renders/$QUALITY/interp/doors" "$i")"          "$(printf '%s/f_%04d.png' "$ROOT/renders/$QUALITY/interp/doors" "$i")"
    done
    cp -f "$src"/f_*.png "$ROOT/renders/$QUALITY/interp/doors/"   # real renders override interpolation
    src="$ROOT/renders/$QUALITY/interp/doors"
  fi
  encode_seq "$src" "$STATIC/doors/desktop" 1920 85 "$n_doors"
  encode_seq "$src" "$STATIC/doors/mobile" 960 78 "$n_doors"
  ffmpeg -hide_banner -loglevel error -y -i "$src/f_0001.png" -vf "scale='min(1920,iw)':-2:flags=lanczos" \
    -c:v libwebp -quality 82 "$STATIC/doors/desktop/poster.webp"
  ffmpeg -hide_banner -loglevel error -y -i "$src/f_0001.png" -vf "scale='min(960,iw)':-2:flags=lanczos" \
    -c:v libwebp -quality 78 "$STATIC/doors/mobile/poster.webp"
  local w
  for w in 1920 960; do   # door video (DECISIONS D35): VP9 WebM first, H.264 MP4 fallback
    ffmpeg -hide_banner -loglevel error -y -framerate 24 -start_number 1 -i "$src/f_%04d.png" \
      -vf "scale='min(${w},iw)':-2:flags=lanczos" -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p -an \
      "$STATIC/doors/doors-$w.webm"
    ffmpeg -hide_banner -loglevel error -y -framerate 24 -start_number 1 -i "$src/f_%04d.png" \
      -vf "scale='min(${w},iw)':-2:flags=lanczos" -c:v libx264 -crf 24 -preset slow -profile:v high -pix_fmt yuv420p \
      -movflags +faststart -an "$STATIC/doors/doors-$w.mp4"
  done
  log "door video + posters written"
}

encode_props() {
  local src="$ROOT/renders/$QUALITY/props" f
  [[ -d "$src" ]] || { log "no prop renders yet (skipping props)"; return 0; }
  mkdir -p "$STATIC/props"
  for f in "$src"/*.png; do
    ffmpeg -hide_banner -loglevel error -y -i "$f" -c:v libwebp -quality 90 -pix_fmt yuva420p \
      "$STATIC/props/$(basename "${f%.png}").webp"
  done
  log "encoded $(ls "$STATIC/props"/*.webp | wc -l | tr -d ' ') prop sprites"
}

main() {
  parse_args "$@"
  require_ffmpeg
  command -v node >/dev/null 2>&1 || die "node is required to write frames.json"
  if (( INTERP )); then interpolate_steps; fi
  encode_steps
  if (( NO_DOORS )); then log "skipping doors (--no-doors)"; else encode_doors; fi
  encode_props
  node "$ROOT/scripts/build_frames_json.mjs" --manifest "$ROOT/renders/manifest.json" --static "$STATIC" \
    --out "$ROOT/web/src/lib/frames.json"
  log "encode_frames complete"
}

main "$@"
