"""Render the Golu fly-through frames per step (SPEC §4.8, DECISIONS D27).

blender -b -P blender/render_steps.py -- --quality draft|final --steps 1-9 [--stride N] [--no-resume] [--probe]
Each stepN/ holds its 96 hold frames + 24 outgoing transition frames (step 9: + 72 finale frames).
--probe renders three representative frames at the chosen quality and prints seconds per frame (used by
render_all.sh to print the total estimate before a final render).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402

from lib import config as C  # noqa: E402
from lib import render as R  # noqa: E402


def ensure_built(args: C.CliArgs) -> Path:
    blend = args.out / f"golu_{C.scene_quality(args.quality)}.blend"
    want = C.config_hash(args.config)
    if blend.exists():
        bpy.ops.wm.open_mainfile(filepath=str(blend))
        if bpy.context.scene.get("config_hash") == want and (args.out / "manifest.json").exists():
            return blend
        R.log("built scene is stale (config or scripts changed); rebuilding")
    cmd = [bpy.app.binary_path, "-b", "--factory-startup", "--python-exit-code", "1", "-P",
           str(C.BLENDER_DIR / "build_scene.py"), "--", "--config", str(args.config), "--quality", C.scene_quality(args.quality),
           "--out", str(args.out)]
    subprocess.run(cmd, check=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    return blend


def frames_for_step(manifest: dict, step: int) -> list[tuple[int, int]]:
    """(blender_frame, local_index 1-based) for every frame stored under stepN/."""
    st = manifest["steps"][step - 1]
    start = st["global_start"] + 1
    return [(start + i, i + 1) for i in range(st["count"])]


def render_frames(scene, frames: list[tuple[int, int]], out_dir: Path, args: C.CliArgs, label: str) -> None:
    todo = frames[::args.stride]
    log = R.ProgressLog(len(todo), label)
    for gframe, local in todo:
        path = out_dir / f"f_{local:04d}.png"
        if args.resume and R.is_frame_done(path):
            log.tick(0.0, skipped=True)
            continue
        scene.frame_set(gframe)
        secs = R.render_still(scene, path)
        log.tick(secs)


def probe(scene, manifest: dict, out: Path) -> float:
    picks = [manifest["steps"][0]["global_start"] + 49, manifest["steps"][8]["global_start"] + 49, manifest["total"]]
    times = []
    for f in picks:
        scene.frame_set(f)
        times.append(R.render_still(scene, out / "probe" / f"probe_{f:04d}.png"))
    mean = sum(times) / len(times)
    print(f"PROBE seconds_per_frame={mean:.2f} samples={times}")
    return mean


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv)
    ensure_built(args)
    scene = bpy.context.scene
    R.apply_quality(scene, args.quality)
    R.setup_color_management(scene)
    R.setup_glare(scene, True)
    manifest = json.loads((args.out / "manifest.json").read_text(encoding="utf-8"))
    root = args.out / args.quality / "steps"
    if args.probe:
        probe(scene, manifest, args.out / args.quality)
        return 0
    t0 = time.time()
    for n in args.steps:
        frames = frames_for_step(manifest, n)
        if args.frames:
            frames = [fr for fr in frames if fr[1] in set(args.frames)]
        render_frames(scene, frames, root / f"step{n}", args, f"step {n}")
    R.log(f"done in {(time.time() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
