"""Transparent ritual & prasadam sprites (SPEC §4.7, DECISIONS D31).

blender -b -P blender/render_props.py -- [--quality draft|final] [--only NAME] [--verify]
1024×1024 (petals 256×256), film transparent, top-down three-quarter view. Bowls and trays carry a soft
contact shadow via a shadow catcher; the plates float (they are waved), so they have none.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from lib import config as C  # noqa: E402
from lib import materials as M  # noqa: E402
from lib import mesh_utils as MU  # noqa: E402
from lib import props as PR  # noqa: E402
from lib import qa as Q  # noqa: E402
from lib import render as R  # noqa: E402

SPRITES = ["aarthi_plate", "camphor_plate", "bowl_sundal", "bowl_sakkarai_pongal", "bowl_puliyodarai",
           "bowl_curd_rice", "bowl_sambar_rice", "tray_banana_leaf", "tray_composite", "petal_marigold",
           "petal_rose", "flower_jasmine"]
PETALS = {"petal_marigold", "petal_rose", "flower_jasmine"}


# --------------------------------------------------------------------------- scene


def sprite_scene(cfg: C.GoluConfig, quality: str, res: int) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    M.init(cfg)
    R.setup_color_management(scene, exposure=0.0)
    R.apply_quality(scene, "final" if quality == "final" else "draft", transparent=True, resolution=(res, res),
                    engine="CYCLES", samples=96 if quality == "final" else 32)
    R.setup_glare(scene, False)
    # warm studio surround: brass and silver need something bright to reflect (the film stays transparent)
    warm = R.kelvin_to_rgb(cfg.palette.kelvin("key"))
    R.setup_world_color(scene, tuple(c * 0.45 for c in warm), 1.0)
    scene.render.film_transparent = True
    col = MU.ensure_collection("Sprite")
    from lib.environment import _area_light
    P_ = cfg.palette
    _area_light("S_Key", (0.5, 0.5), (-0.45, -0.55, 0.75), Vector((0, 0, 0.02)), P_.kelvin("key"), 30, col)
    _area_light("S_Rim", (0.3, 0.3), (0.4, 0.45, 0.45), Vector((0, 0, 0.03)), P_.kelvin("rim"), 10, col, 0.5, 1.4)
    _area_light("S_Fill", (0.6, 0.6), (0.6, -0.4, 0.3), Vector((0, 0, 0.02)), P_.kelvin("fill"), 4, col)
    cam = bpy.data.objects.new("S_Cam", bpy.data.cameras.new("S_Cam"))
    cam.data.lens = 45
    col.objects.link(cam)
    scene.camera = cam
    return scene


def frame_sprite(scene, objs: list[bpy.types.Object], elevation_deg: float = 38, azimuth_deg: float = 30,
                 margin: float = 1.12) -> None:
    """Top-down three-quarter camera fitted to the object bounds."""
    bpy.context.view_layer.update()
    pts = []
    for o in objs:
        lo, hi = MU.bounds_world(o)
        pts += [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    centre = sum(pts, Vector()) / len(pts)
    radius = max((p - centre).length for p in pts) * margin * 0.82   # bounding-box corners overestimate
    cam = scene.camera
    fov = 2 * math.atan(cam.data.sensor_width / (2 * cam.data.lens))
    dist = radius / math.sin(fov / 2)
    el, az = math.radians(elevation_deg), math.radians(azimuth_deg)
    eye = centre + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    cam.matrix_world = Q.look_at(eye, centre)
    cam.data.clip_start = max(1e-4, dist * 0.02)     # petals are ~2 cm: the default 0.1 m would clip them away
    cam.data.clip_end = dist * 20 + 1.0


def fade_shadow_border(path: Path, band: float = 0.08) -> None:
    """Fade the contact shadow to zero alpha near the frame edge so the sprite never shows a cut-off square.
    Only shadow-catcher pixels change: they are black with alpha; the brass and food are never near-black."""
    import numpy as np
    a = Q.load_rgba(path)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy)).astype(np.float32)
    t = np.clip(edge / (band * w), 0.0, 1.0)
    window = t * t * (3 - 2 * t)                       # smoothstep
    lum = a[..., :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    shadow = lum < 0.03
    a[..., 3] = np.where(shadow, a[..., 3] * window, a[..., 3])
    Q.save_rgba(a, path)


def shadow_catcher(size: float = 0.6) -> bpy.types.Object:
    ob = MU.grid("ShadowCatcher", size, size, 1, 1)
    ob.is_shadow_catcher = True
    MU.assign_material(ob, M.simple("M_Catcher", (0.5, 0.5, 0.5), 0.8))
    return ob


# --------------------------------------------------------------------------- props


def brass_plate(name: str, radius: float, rim: float, emboss: bool) -> bpy.types.Object:
    prof = [(0.0, 0.0), (radius * 0.75, 0.0), (radius * 0.92, 0.004), (radius, rim), (radius * 1.04, rim + 0.002),
            (radius * 1.02, rim + 0.004), (radius * 0.95, 0.006), (0.0, 0.004)]
    bm = MU.lathe_bm(prof, 96)
    if emboss:
        for v in bm.verts:
            r = math.hypot(v.co.x, v.co.y)
            if radius * 0.55 < r < radius * 0.85 and v.co.z > 0.003:
                a = math.atan2(v.co.y, v.co.x)
                v.co.z += 0.0012 * max(0.0, math.cos(a * 16))
    ob = MU.bmesh_to_object(bm, name)
    MU.shade_smooth(ob, 50)
    MU.assign_material(ob, M.brass())
    return ob


def powder_mound(name: str, r: float, h: float, mat, at: Vector) -> bpy.types.Object:
    ob = MU.lathe(name, [(0.0, 0.0), (r, 0.0), (r * 0.6, h * 0.55), (0.0, h)], 24, screw=False)
    MU.displace(ob, MU.texture(f"tx_{name}", "CLOUDS", noise_scale=0.004), 0.0015)
    ob.location = at
    MU.assign_material(ob, mat)
    return ob


def build_aarthi_plate(cfg, rng) -> list[bpy.types.Object]:
    """Brass thattu with an UNLIT ghee lamp (the flame is live in the web app), kumkum, turmeric and flowers."""
    plate = brass_plate("aarthi_thattu", 0.11, 0.014, True)
    lamp = MU.lathe("aarthi_lamp", [(0.0, 0.0), (0.016, 0.0), (0.012, 0.01), (0.008, 0.016), (0.024, 0.026),
                                    (0.03, 0.034), (0.026, 0.036), (0.0, 0.03)], 32, screw=False)
    MU.assign_material(lamp, M.brass())
    wick = MU.tube("aarthi_wick", [Vector((0.016, 0.0, 0.032)), Vector((0.032, 0.0, 0.041))], 0.0028)
    MU.assign_material(wick, M.cotton_wick())
    kum = powder_mound("aarthi_kumkum", 0.024, 0.016, M.powder("kumkum-powder"), Vector((-0.058, -0.03, 0.005)))
    tur = powder_mound("aarthi_turmeric", 0.024, 0.016, M.powder("turmeric-powder"), Vector((-0.05, 0.04, 0.005)))
    out = [plate, lamp, wick, kum, tur]
    for i in range(7):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.05, 0.085)
        f = PR.make_marigold_head(f"aarthi_m{i}", "marigold-orange" if i % 2 else "marigold-yellow", rng, 0.012)
        f.location = (math.cos(a) * r, math.sin(a) * r, 0.01)
        out.append(f)
    for i in range(10):
        b = PR.make_jasmine_bud(f"aarthi_j{i}", rng, 0.014)
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.035, 0.08)
        b.location = (math.cos(a) * r, math.sin(a) * r, 0.008)
        b.rotation_euler = (math.pi / 2, 0, rng.uniform(0, math.tau))
        out.append(b)
    for i in range(14):
        pet = MU.uv_sphere(f"aarthi_rose{i}", 0.006, 10, 6, scale=(1.4, 1.0, 0.25))
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.02, 0.09)
        pet.location = (math.cos(a) * r, math.sin(a) * r, 0.0065)
        pet.rotation_euler = (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 6))
        MU.assign_material(pet, M.simple("M_RosePetal", (0.55, 0.02, 0.06), 0.45, sss=0.2))
        out.append(pet)
    return out


def build_camphor_plate(cfg, rng) -> list[bpy.types.Object]:
    plate = brass_plate("camphor_plate", 0.07, 0.01, False)
    tab = MU.box("camphor_tablet", (0.022, 0.022, 0.012), (0, 0, 0.012), bevel=0.003, bevel_segments=3)
    MU.displace(tab, MU.texture("tx_camphor", "CLOUDS", noise_scale=0.003), 0.0008)
    MU.assign_material(tab, M.food("camphor"))
    handle = MU.tube("camphor_handle", [Vector((0.07, 0, 0.008)), Vector((0.1, 0, 0.012)), Vector((0.12, 0, 0.02))], 0.004)
    MU.assign_material(handle, M.brass())
    return [plate, tab, handle]


def build_bowl(kind: str) -> bpy.types.Object:
    prof = [(0.0, 0.0), (0.026, 0.0), (0.028, 0.006), (0.03, 0.008), (0.05, 0.03), (0.058, 0.046), (0.061, 0.05),
            (0.058, 0.051), (0.054, 0.046), (0.046, 0.032), (0.026, 0.014), (0.0, 0.012)]
    ob = MU.lathe(f"bowl_{kind}", prof, 64, screw=False)
    MU.assign_material(ob, M.brass() if kind == "brass" else M.silver())
    return ob


FOODS = {
    "sundal": [("chickpea", 0.0042, (1.0, 0.95, 0.9), 1600), ("coconut", 0.0034, (1.7, 1.0, 0.3), 420),
               ("curry_leaf", 0.0075, (1.0, 0.42, 0.06), 140), ("mustard", 0.0014, (1, 1, 1), 500)],
    "sakkarai_pongal": [("pongal_rice", 0.0028, (1.0, 0.45, 0.42), 5000), ("cashew", 0.0045, (1.2, 0.6, 0.55), 40),
                        ("raisin", 0.0028, (1.0, 0.8, 0.7), 60)],
    "puliyodarai": [("tamarind_rice", 0.0026, (1.0, 0.45, 0.42), 5000), ("peanut", 0.0035, (1.0, 0.8, 0.6), 120),
                    ("curry_leaf", 0.006, (1.0, 0.45, 0.06), 60), ("red_chilli", 0.004, (2.2, 0.6, 0.6), 8)],
    "curd_rice": [("curd_rice", 0.0026, (1.0, 0.45, 0.42), 5000), ("pomegranate", 0.0028, (1.0, 0.9, 1.1), 90),
                  ("mustard", 0.0012, (1, 1, 1), 150), ("curry_leaf", 0.005, (1.0, 0.45, 0.06), 25)],
    "sambar_rice": [("sambar_rice", 0.0032, (1.0, 0.7, 0.6), 3500), ("drumstick", 0.004, (2.6, 0.8, 0.8), 20),
                    ("carrot", 0.004, (1, 1, 1), 40), ("curry_leaf", 0.005, (1.0, 0.45, 0.06), 30)],
}


def _grain(name: str, size: float, scale: tuple, kind: str, rng: random.Random) -> bpy.types.Object:
    if kind in ("curry_leaf", "coconut"):
        ob = MU.uv_sphere(name, size, 10, 6, scale=scale)
    elif kind == "chickpea":
        ob = MU.ico_sphere(name, size, 2)
        MU.displace(ob, MU.texture(f"tx_{name}", "CLOUDS", noise_scale=0.0025), size * 0.2)
        ob.scale = scale
    elif kind == "carrot":
        ob = MU.box(name, (size * 2, size * 2, size * 2), (0, 0, 0), bevel=size * 0.3)
    else:
        ob = MU.uv_sphere(name, size, 10, 6, scale=scale)
    MU.apply_transform(ob)
    MU.assign_material(ob, M.food(kind))
    return ob


def build_food(dish: str, rng: random.Random, seed: int) -> list[bpy.types.Object]:
    """Food mound inside the bowl + GN scatter (Poisson, two layers) of grains/garnish (D21)."""
    mound_mat = {"sundal": "chickpea", "sakkarai_pongal": "pongal_rice", "puliyodarai": "tamarind_rice",
                 "curd_rice": "curd_rice", "sambar_rice": "sambar_rice"}[dish]
    # follows the bowl's inner wall (open base, so nothing is scattered underneath) and domes just above the rim
    dome = MU.lathe(f"mound_{dish}", [(0.026, 0.015), (0.0365, 0.024), (0.045, 0.035), (0.0512, 0.0455),
                                      (0.046, 0.053), (0.033, 0.06), (0.016, 0.0635), (0.0, 0.064)], 48, screw=False)
    MU.displace(dome, MU.texture(f"tx_mound_{dish}", "CLOUDS", noise_scale=0.012), 0.004)
    MU.assign_material(dome, M.food(mound_mat))
    out = [dome]
    for layer, offset in enumerate((0.0, 0.0035)):
        for k, (kind, size, scale, count) in enumerate(FOODS[dish]):
            if layer == 1 and k > 0:
                continue
            srcs = [_grain(f"g_{dish}_{kind}_{layer}_{v}", size * rng.uniform(0.9, 1.1), scale, kind, rng)
                    for v in range(3)]
            lib = MU.instance_collection(f"Lib_{dish}_{kind}_{layer}", srcs)
            surf = bpy.data.objects.new(f"scatter_{dish}_{kind}_{layer}", dome.data.copy())
            bpy.context.scene.collection.objects.link(surf)
            area = math.pi * 0.052 ** 2 * 1.15
            tree = MU.scatter_tree(f"GN_{dish}_{kind}_{layer}", seed + k * 17 + layer, source="faces", collection=lib,
                                   density=count / area, min_dist=size * (1.4 if kind not in ("mustard",) else 1.0),
                                   scale_range=(0.85, 1.15), align_to_normal=True,
                                   random_rot=(0.8, 0.8, math.tau), offset_along_normal=offset + size * 0.35)
            MU.add_gn_modifier(surf, tree)
            surf.data.materials.clear()
            out.append(surf)
    if dish == "sakkarai_pongal":   # ghee sheen pooling on top
        ghee = MU.uv_sphere("ghee_film", 0.035, 24, 8, scale=(1, 1, 0.12))
        ghee.location = (0.004, -0.004, 0.051)
        MU.assign_material(ghee, M.food("ghee_film"))
        out.append(ghee)
    return out


def build_banana_leaf_tray(cfg, rng) -> list[bpy.types.Object]:
    tray = brass_plate("tray", 0.2, 0.012, False)
    tray.scale = (1.0, 0.62, 1.0)
    leaf = MU.grid("tray_leaf", 0.36, 0.2, 36, 20)
    for v in leaf.data.vertices:
        v.co.z = 0.008 + 0.012 * (abs(v.co.y) / 0.1) ** 2 + 0.004 * math.sin(v.co.x * 40) * (abs(v.co.y) / 0.1)
    MU.solidify(leaf, 0.0012)
    MU.set_uv_from(leaf, lambda co: (co.y / 0.2 + 0.5, co.x / 0.36 + 0.5))
    MU.shade_smooth(leaf, None)
    MU.assign_material(leaf, M.banana_leaf())
    return [tray, leaf]


def build_petal(kind: str, rng) -> list[bpy.types.Object]:
    from lib import attributes as A
    if kind == "flower_jasmine":
        parts = []
        for i in range(5):
            pet = A.leaf_shell(f"jas_p{i}", 0.012, 0.006, cup=0.4)
            pet.rotation_euler = (1.35, 0, i / 5 * math.tau)
            MU.apply_transform(pet)
            parts.append(pet)
        ob = MU.join(parts, "flower_jasmine")
        MU.assign_material(ob, M.jasmine())
        return [ob]
    pet = A.leaf_shell(kind, 0.022, 0.016 if kind == "petal_rose" else 0.009, cup=0.5, tip_pointed=kind != "petal_rose")
    pet.rotation_euler = (1.2, 0.3, 0.4)
    MU.apply_transform(pet)
    MU.assign_material(pet, M.simple("M_RosePetal", (0.55, 0.02, 0.06), 0.45, sss=0.2) if kind == "petal_rose"
                       else M.marigold("marigold-orange"))
    return [pet]


# --------------------------------------------------------------------------- render + verify


def render_sprite(name: str, cfg: C.GoluConfig, quality: str, out: Path) -> Path:
    res = 256 if name in PETALS else 1024
    scene = sprite_scene(cfg, quality, res)
    rng = C.rng_for("sprite", name)
    pr = cfg.prasadam
    dishes = {d["id"]: d for d in pr["dishes"]}
    objs: list[bpy.types.Object] = []
    catcher = False
    elevation = 38
    if name == "aarthi_plate":
        objs = build_aarthi_plate(cfg, rng)
    elif name == "camphor_plate":
        objs = build_camphor_plate(cfg, rng)
    elif name.startswith("bowl_"):
        dish = name[5:]
        bowl = build_bowl(dishes[dish]["bowl"])
        objs = [bowl] + build_food(dish, rng, C.seed_for("food", dish))
        catcher = True
    elif name == "tray_banana_leaf":
        objs = build_banana_leaf_tray(cfg, rng)
        catcher = True
        elevation = 48
    elif name == "tray_composite":
        objs = build_banana_leaf_tray(cfg, rng)
        trio = list(pr["fixed"]) + [pr["third_dish"]]
        for i, dish in enumerate(trio):
            x = (i - 1) * 0.11
            bowl = build_bowl(dishes[dish]["bowl"])
            food = build_food(dish, C.rng_for("sprite", "bowl_" + dish), C.seed_for("food", dish))
            for o in [bowl] + food:
                o.location += Vector((x, 0.0, 0.006))
            objs += [bowl] + food
        catcher = True
        elevation = 48
    elif name in PETALS:
        objs = build_petal(name, rng)
        elevation = 60
    else:
        raise KeyError(name)
    if catcher:
        shadow_catcher(0.9)
    real = [o for o in objs if o.type == "MESH" and len(o.data.vertices)]
    frame_sprite(scene, real, elevation, 30, 1.12 if catcher else (1.3 if name in PETALS else 1.08))
    path = out / f"{name}.png"
    secs = R.render_still(scene, path)
    if catcher:
        fade_shadow_border(path)
    R.log(f"sprite {name} rendered in {secs:.1f}s")
    return path


def verify(out_dir: Path) -> list[str]:
    errs = []
    for name in SPRITES:
        p = out_dir / f"{name}.png"
        if not p.exists():
            errs.append(f"{name}: missing")
            continue
        rep = Q.alpha_report(p)
        print(f"ALPHA {name}: {rep}")
        if rep["border_max_alpha"] > 0.02:
            errs.append(f"{name}: touches the frame edge (border alpha {rep['border_max_alpha']:.2f})")
        if rep["islands"] > (3 if name in PETALS else 1):
            errs.append(f"{name}: {rep['islands']} alpha islands (stray geometry)")
        if rep["fringe_dl"] > 0.15:
            errs.append(f"{name}: edge fringe ΔL {rep['fringe_dl']:.2f} (halo)")
    return errs


def composite_preview(out_dir: Path) -> Path:
    """Each sprite over magenta, black and white for the edge inspection sheet."""
    import numpy as np
    tiles = []
    for name in SPRITES:
        a = Q.load_rgba(out_dir / f"{name}.png")
        for bg in ((1.0, 0.0, 1.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)):
            al = a[..., 3:4]
            comp = np.concatenate([a[..., :3] * al + np.array(bg) * (1 - al), np.ones_like(al)], axis=-1)
            p = out_dir / "_composites" / f"{name}_{int(bg[0])}{int(bg[1])}{int(bg[2])}.png"
            Q.save_rgba(comp, p)
            tiles.append(p)
    return Q.contact_sheet(tiles, 6, C.ROOT / "renders" / "qa" / "sprites_on_bg.png", 256)


def main(argv: list[str]) -> int:
    args = C.parse_cli(argv)
    cfg = C.load_config(args.config)
    out = args.out / args.quality / "props"
    names = args.only or SPRITES
    for n in names:
        render_sprite(n, cfg, args.quality, out)
    if args.verify:
        errs = verify(out)
        composite_preview(out)
        for e in errs:
            print("SPRITE FAIL:", e)
        print(f"SPRITES: {'PASS' if not errs else str(len(errs)) + ' failures'}")
        return 1 if errs else 0
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
