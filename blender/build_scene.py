"""Entry point: builds the whole Golu .blend from config (SPEC §4.1).

blender -b -P blender/build_scene.py -- --config content/golu.config.json [--quality draft|final]
        [--empty] [--verify] [--qa-stills] [--only id1,id2]
"""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402

from lib import camera as CAM  # noqa: E402
from lib import config as C  # noqa: E402
from lib import dioramas as DI  # noqa: E402
from lib import environment as E  # noqa: E402
from lib import materials as M  # noqa: E402
from lib import mesh_utils as MU  # noqa: E402
from lib import qa as Q  # noqa: E402
from lib import render as R  # noqa: E402


@dataclass
class BuildResult:
    env: E.EnvironmentHandles
    dolls: dict[str, bpy.types.Object] = field(default_factory=dict)
    steps: list = field(default_factory=list)
    timeline: CAM.Timeline | None = None
    manifest: dict | None = None
    blend: Path | None = None


def reset_scene(cfg: C.GoluConfig) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.name = "Golu"
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = int(cfg.raw["meta"]["fps"])
    scene.frame_start = 1
    scene.frame_end = 1
    return scene


def build(cfg: C.GoluConfig, args: C.CliArgs, scene: bpy.types.Scene) -> BuildResult:
    t0 = time.time()
    M.init(cfg)
    env = E.build_environment(cfg, scene)
    R.log(f"environment built in {time.time() - t0:.1f}s")
    result = BuildResult(env=env)
    if args.empty:
        return result
    t1 = time.time()
    only = set(args.only) if args.only else None
    result.steps = DI.build_all(cfg, env.steps, only)
    result.dolls = {p.spec.id: p.obj for r in result.steps for p in r.placed}
    R.log(f"{len(result.dolls)} dolls + dioramas built in {time.time() - t1:.1f}s")
    cam, focus = CAM.build_rig(cfg, scene)
    shots = []
    for r in result.steps:
        shots.append(CAM.plan_shot(cfg, r.handle, [p.obj for p in r.placed]))
    result.timeline = CAM.build_timeline(cfg)
    CAM.keyframe_all(cfg, scene, cam, focus, shots, result.timeline, CAM.establishing_pose(cfg, env.steps))
    return result


def save(scene: bpy.types.Scene, path: Path, cfg_hash: str) -> None:
    scene["config_hash"] = cfg_hash
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True, relative_remap=True)
    R.log(f"saved {path}")


def verify(cfg: C.GoluConfig, result: BuildResult) -> list[str]:
    errs: list[str] = []
    env = result.env
    lay = cfg.layout
    widths = [s.width for s in env.steps]
    if len(env.steps) != 9:
        errs.append(f"{len(env.steps)} tiers (expected 9)")
    for a, b in zip(widths, widths[1:]):
        if not abs((a - b) - (lay["width_bottom"] - lay["width_top"]) / 8) < 1e-6:
            errs.append("tier widths do not step evenly")
            break
    names = {o.name for o in bpy.data.objects}
    for s in env.steps:
        for prefix in ("Cloth_", "Trim_", "Garland_", "Tier_"):
            if f"{prefix}{s.n}" not in names:
                errs.append(f"missing {prefix}{s.n}")
        cloth = bpy.data.objects.get(f"Cloth_{s.n}")
        if cloth and cloth.active_material and not cloth.active_material.name.startswith("M_Silk_"):
            errs.append(f"Cloth_{s.n} not silk")
    if len(env.lamps) != 2:
        errs.append(f"{len(env.lamps)} kuthuvilakku (expected 2)")
    lamp_flames = [o for o in bpy.data.objects if o.name.startswith("Kuthuvilakku_") and o.get("is_flame")]
    if len(lamp_flames) != 2 * lay["kuthuvilakku"]["wicks"]:
        errs.append(f"{len(lamp_flames)} kuthuvilakku flames (expected 10)")
    agal = [o for o in bpy.data.objects if o.name.startswith("Agal_") and o.get("is_flame")]
    if len(agal) < 18:
        errs.append(f"only {len(agal)} lit agal niches")
    for nm in ("Thoranam", "Banana_-1", "Banana_1", "Kolam_Floor", "Key", "Rim_L", "Rim_R", "Fill"):
        if nm not in names:
            errs.append(f"missing {nm}")
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.users_collection]
    verts = sum(len(o.data.vertices) for o in meshes)
    print(f"VERIFY STATS: objects={len(bpy.data.objects)} meshes={len(meshes)} vertices={verts}")
    return errs


def verify_manifest(cfg: C.GoluConfig, result: BuildResult) -> list[str]:
    errs = []
    m = result.manifest or {}
    if m.get("total") != 1128:
        errs.append(f"manifest total {m.get('total')} (expected 1128)")
    expect = 0
    for st in m.get("steps", []):
        if st["global_start"] != expect:
            errs.append(f"step {st['id']}: global_start {st['global_start']} (expected {expect})")
        expect += st["count"]
        for did, tr in st["hotspots"].items():
            vis = sum(v for _, _, v in tr["t"]) / max(len(tr["t"]), 1)
            if vis < 0.3:
                errs.append(f"{did}: visible in only {vis:.0%} of its hold samples")
    return errs


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv)
    cfg = C.load_config(args.config)
    scene = reset_scene(cfg)
    result = build(cfg, args, scene)
    R.setup_color_management(scene)
    R.apply_quality(scene, args.quality)
    R.setup_glare(scene, True)
    if not args.empty:
        step_dolls = {r.handle.n: [p.obj for p in r.placed] for r in result.steps}
        lamp_flames = [o for o in result.env.flame_points]
        result.manifest = CAM.write_manifest(args.out / "manifest.json", cfg, result.timeline, step_dolls, lamp_flames,
                                             scene, scene.camera)
        R.log(f"manifest written: {result.timeline.total} frames")
    tag = "empty_" if args.empty else ""
    blend = args.out / f"golu_{tag}{args.quality}.blend"
    save(scene, blend, C.config_hash(args.config))
    result.blend = blend
    rc = 0
    if args.verify:
        errs = verify(cfg, result)
        if not args.empty:
            errs += DI.verify_placement(cfg, result.steps) if not args.only else []
            errs += verify_manifest(cfg, result)
        for e in errs:
            print(f"VERIFY FAIL: {e}")
        print(f"VERIFY: {'PASS' if not errs else f'{len(errs)} errors'}")
        rc = 1 if errs else 0
    if args.qa_stills:
        out = args.out / "qa"
        paths = Q.render_stills(scene, Q.qa_cameras(cfg.layout), out, prefix="phase1_" if args.empty else "")
        for p in paths:
            stats = Q.image_stats(p)
            problems = Q.assert_warm(stats)
            print(f"QA {p.name}: " + ", ".join(f"{k}={v:.3f}" for k, v in stats.items()))
            for pr in problems:
                print(f"QA WARN {p.name}: {pr}")
    return rc


if __name__ == "__main__":
    try:
        code = main(sys.argv)
    except Exception:
        import traceback
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.exit(code)
