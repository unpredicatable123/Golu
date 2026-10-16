"""Room, nine draped tiers, decorations, lamps and lighting (SPEC §4.2, PLAN §1.1/§2)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Vector

from . import materials as M
from . import mesh_utils as MU
from . import props as P
from . import render as R
from .config import GoluConfig, rng_for, seed_for


@dataclass
class StepHandle:
    n: int
    width: float
    z_top: float
    y_front: float
    depth: float
    usable: float
    tread_obj: bpy.types.Object | None = None
    cloth_obj: bpy.types.Object | None = None

    @property
    def y_back(self) -> float:
        return self.y_front + self.depth

    def front_line(self, row: str, layout: dict) -> float:
        return self.y_front + 0.09 + (layout["back_row_offset"] if row == "back" else 0.0)


@dataclass
class EnvironmentHandles:
    steps: list[StepHandle]
    lamps: list[bpy.types.Object] = field(default_factory=list)
    flame_points: list[bpy.types.Object] = field(default_factory=list)
    lights: list[bpy.types.Object] = field(default_factory=list)
    collection: bpy.types.Collection | None = None
    wall_y: float = 0.0
    front_wall_y: float = -8.0


# --------------------------------------------------------------------------- geometry of the golu


def step_geometry(layout: dict) -> list[StepHandle]:
    n = layout["step_count"]
    wb, wt = layout["width_bottom"], layout["width_top"]
    out = []
    for i in range(1, n + 1):
        w = wb - (i - 1) * (wb - wt) / (n - 1)
        out.append(StepHandle(n=i, width=w, z_top=i * layout["rise"], y_front=-(n - i) * layout["tread"],
                              depth=layout["tread"], usable=w * layout["usable_width_ratio"]))
    return out


def build_steps(cfg: GoluConfig, col) -> list[StepHandle]:
    steps = step_geometry(cfg.layout)
    wall_y = cfg.layout["tread"]
    for s in steps:
        depth = wall_y - s.y_front
        ob = MU.box(f"Tier_{s.n}", (s.width, depth, s.z_top), (0, s.y_front + depth / 2, s.z_top / 2),
                    col, bevel=0.003)
        MU.assign_material(ob, M.teak())
        s.tread_obj = ob
    return steps


def build_cloth_drape(cfg: GoluConfig, s: StepHandle, color_key: str, col) -> bpy.types.Object:
    """Silk drape over the tread and down the riser; folds by Displace (DECISIONS D23); zari at UV v>0.9."""
    lay = cfg.layout
    over = lay["cloth_overhang_sides"]
    w = s.width + 2 * over
    tread_len = s.depth + 0.02
    hang = lay["rise"] * 0.93
    corner_r = 0.012
    nu, nv = 320, 64
    path_len = tread_len + hang + corner_r * math.pi / 2
    rng = rng_for("cloth", s.n)
    hooks = max(3, round(s.width / 0.42))
    pitch = (s.width + 0.06) / hooks
    ph1, ph2, ph3 = rng.uniform(0, math.tau), rng.uniform(0, math.tau), rng.uniform(0, math.tau)

    def fold(x: float, hw: float) -> tuple[float, float]:
        """Outward fold depth and hem lift for a point x on the hanging part (hw: 0 at edge → 1 at hem)."""
        k = (x + s.width / 2 + 0.03) / pitch
        near_hook = abs(math.cos(math.pi * k)) ** 6          # folds bunch up under each garland hook
        wave = (0.55 * math.sin(math.tau * x / 0.105 + ph1) + 0.3 * math.sin(math.tau * x / 0.047 + ph2)
                + 0.15 * math.sin(math.tau * x / 0.023 + ph3))
        depth = (0.006 + 0.012 * near_hook) * hw ** 1.15 * (0.55 + 0.45 * wave)
        lift = 0.032 * near_hook * hw ** 3                   # scalloped hem lifted at the hooks
        return max(depth, 0.0) + 0.001 * hw, lift

    verts, faces, uvs, weights = [], [], [], []
    for j in range(nv + 1):
        d = j / nv * path_len               # distance along the drape from the back
        if d <= tread_len:
            y, z, hw = s.y_back + 0.02 - d, s.z_top + 0.0025, 0.0
        elif d <= tread_len + corner_r * math.pi / 2:
            a = (d - tread_len) / corner_r
            y = s.y_front - math.sin(a) * corner_r
            z = s.z_top + 0.0025 - (1 - math.cos(a)) * corner_r
            hw = 0.0
        else:
            dd = d - tread_len - corner_r * math.pi / 2
            y, z = s.y_front - corner_r - 0.0025, s.z_top - corner_r - dd
            hw = dd / hang
        for i in range(nu + 1):
            u = i / nu
            x = (u - 0.5) * w
            # side overhang drops down past the tier edge
            side = max(0.0, abs(x) - s.width / 2)
            dy, lift = fold(x, min(1.0, hw)) if hw > 0 else (0.0, 0.0)
            verts.append((x, y - dy, z - side * 1.6 + lift))
            uvs.append((u, d / path_len))
            weights.append(min(1.0, hw) ** 1.3)
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + nu + 1, a + nu + 2, a + 1))
    ob = MU.new_mesh_object(f"Cloth_{s.n}", verts, faces, col)
    uv = ob.data.uv_layers.new(name="UVMap")
    for li, loop in enumerate(ob.data.loops):
        uv.data[li].uv = uvs[loop.vertex_index]
    vg = ob.vertex_groups.new(name="hang")
    for vi, wt in enumerate(weights):
        if wt > 0:
            vg.add([vi], wt, "REPLACE")
    # Displace with a noise texture softens the folds into cloth (plus a faint tread ripple everywhere)
    tex = MU.texture(f"tx_soft_{s.n}", "CLOUDS", noise_scale=0.09, noise_depth=2)
    m = ob.modifiers.new("Soft", "DISPLACE")
    m.texture, m.texture_coords, m.strength, m.direction, m.mid_level = tex, "GLOBAL", 0.006, "Y", 0.5
    m.vertex_group = "hang"
    tex2 = MU.texture(f"tx_ripple_{s.n}", "CLOUDS", noise_scale=0.05)
    m2 = ob.modifiers.new("Ripple", "DISPLACE")
    m2.texture, m2.texture_coords, m2.strength, m2.direction, m2.mid_level = tex2, "GLOBAL", 0.0015, "Z", 0.0
    sol = ob.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness, sol.offset = 0.002, -1
    MU.add_subsurf(ob, 0, 1)
    MU.apply_all_modifiers(ob)
    MU.shade_smooth(ob, None)
    MU.assign_material(ob, M.silk(color_key))
    s.cloth_obj = ob
    return ob


def build_brass_trim(s: StepHandle, col) -> bpy.types.Object:
    y = s.y_front - 0.016
    z = s.z_top - 0.006
    ob = MU.tube(f"Trim_{s.n}", [Vector((-s.width / 2 - 0.02, y, z)), Vector((s.width / 2 + 0.02, y, z))],
                 0.0045, collection=col)
    MU.assign_material(ob, M.brass())
    return ob


# --------------------------------------------------------------------------- room


def build_room(cfg: GoluConfig, col) -> tuple[float, float]:
    wall_y = cfg.layout["tread"] + 0.05
    front_y = -8.0
    width, height = 7.0, 3.6
    floor = MU.grid("Floor", width, wall_y - front_y, 4, 4, col)
    floor.location = (0, (wall_y + front_y) / 2, 0)
    MU.assign_material(floor, M.red_oxide())
    back = MU.box("BackWall", (width, 0.1, height), (0, wall_y + 0.05, height / 2), col)
    MU.assign_material(back, M.temple_wall())
    for sx in (-1, 1):
        side = MU.box(f"SideWall_{sx}", (0.1, wall_y - front_y, height),
                      (sx * width / 2, (wall_y + front_y) / 2, height / 2), col)
        MU.assign_material(side, M.temple_wall())
    # front wall with doorway (used by the door sequence, DECISIONS D30)
    door_w, door_h = 1.5, 2.45
    for sx in (-1, 1):
        seg_w = (width - door_w) / 2
        fw = MU.box(f"FrontWall_{sx}", (seg_w, 0.25, height), (sx * (door_w / 2 + seg_w / 2), front_y, height / 2), col)
        MU.assign_material(fw, M.temple_wall())
    lintel = MU.box("FrontWall_lintel", (door_w, 0.25, height - door_h), (0, front_y, door_h + (height - door_h) / 2), col)
    MU.assign_material(lintel, M.temple_wall())
    ceil = MU.box("Ceiling", (width, wall_y - front_y, 0.08), (0, (wall_y + front_y) / 2, height + 0.04), col)
    MU.assign_material(ceil, M.teak())
    for i in range(7):
        y = front_y + 0.6 + i * (wall_y - front_y - 0.8) / 6
        beam = MU.box(f"Beam_{i}", (width, 0.16, 0.18), (0, y, height - 0.09), col, bevel=0.01)
        MU.assign_material(beam, M.teak())
    return wall_y, front_y


def _niche(name: str, w: float, h: float, depth: float, col) -> bpy.types.Object:
    """One carved niche: frame with a horseshoe (kudu) arch, recessed back, pilasters and cornice."""
    parts = []
    t = 0.05
    frame_l = MU.box(name + "_pl", (t, depth, h), (-w / 2 - t / 2, 0, h / 2), col, bevel=0.006)
    frame_r = MU.box(name + "_pr", (t, depth, h), (w / 2 + t / 2, 0, h / 2), col, bevel=0.006)
    sill = MU.box(name + "_sill", (w + 2 * t + 0.04, depth + 0.03, 0.04), (0, -0.015, -0.02), col, bevel=0.005)
    cap_l = MU.box(name + "_capl", (t + 0.03, depth + 0.02, 0.035), (-w / 2 - t / 2, -0.01, h - 0.02), col, bevel=0.006)
    cap_r = MU.box(name + "_capr", (t + 0.03, depth + 0.02, 0.035), (w / 2 + t / 2, -0.01, h - 0.02), col, bevel=0.006)
    # kudu arch: ring of segments over the opening
    arch_pts = []
    for i in range(25):
        a = math.pi * i / 24
        arch_pts.append(Vector((math.cos(a) * w / 2 * 1.08, -depth / 2 + 0.01, h + math.sin(a) * w * 0.62)))
    arch = MU.tube(name + "_arch", arch_pts, 0.022, collection=col)
    finial = MU.uv_sphere(name + "_fin", 0.022, 12, 8, col, (1, 0.7, 1.4))
    finial.location = (0, -depth / 2 + 0.01, h + w * 0.62 + 0.035)
    MU.apply_transform(finial)
    cornice = MU.box(name + "_cor", (w + 2 * t + 0.08, depth + 0.05, 0.05), (0, -0.02, h + w * 0.62 + 0.09), col,
                     bevel=0.008)
    parts = [frame_l, frame_r, sill, cap_l, cap_r, arch, finial, cornice]
    ob = MU.join(parts, name)
    MU.assign_material(ob, M.granite())
    return ob


def build_niche_wall(cfg: GoluConfig, col, wall_y: float) -> list[tuple[bpy.types.Object, Vector]]:
    """Niches around the golu: a row above the top tier and columns at both sides; each holds a lit agal."""
    niches = []
    w, h, depth = 0.26, 0.34, 0.12
    top = cfg.layout["step_count"] * cfg.layout["rise"]
    places = []
    for i in range(10):
        places.append(Vector((-2.43 + i * 0.54, wall_y - depth / 2, top + 0.42)))
    for sx in (-1, 1):
        for j in range(4):
            places.append(Vector((sx * 2.55, wall_y - depth / 2, 0.35 + j * 0.5)))
    for k, p in enumerate(places):
        n = _niche(f"Niche_{k}", w, h, depth, col)
        n.location = p
        back = MU.box(f"NicheBack_{k}", (w, 0.02, h + w * 0.6), (p.x, wall_y - 0.005, p.z + (h + w * 0.6) / 2), col)
        MU.assign_material(back, M.simple("M_NicheBack", (0.28, 0.1, 0.05), 0.85))
        niches.append((n, p))
    return niches


# --------------------------------------------------------------------------- decorations & lamps


def build_decorations(cfg: GoluConfig, steps: list[StepHandle], col, wall_y: float) -> list[bpy.types.Object]:
    out = []
    for s in steps:
        x0, x1 = -s.width / 2 - 0.03, s.width / 2 + 0.03
        hooks = max(3, round(s.width / 0.42))
        path = P.swag_path(x0, x1, s.y_front - 0.03, s.z_top - 0.015, 0.06, hooks)
        g = P.build_garland(f"Garland_{s.n}", path, rng_for("garland", s.n), col, seed_for("garland", s.n))
        out.append(g)
        # short drops at the hook points
        for hi in range(hooks + 1):
            x = x0 + (x1 - x0) * hi / hooks
            drop = [Vector((x, s.y_front - 0.032, s.z_top - 0.015 - d * 0.01)) for d in range(11)]
            out.append(P.build_garland(f"Drop_{s.n}_{hi}", drop, rng_for("drop", s.n, hi), col,
                                       seed_for("drop", s.n, hi), pattern="M12"))
    top = steps[-1]
    out.append(P.build_thoranam("Thoranam", (-1.75, wall_y - 0.08, top.z_top + 0.62),
                                (1.75, wall_y - 0.08, top.z_top + 0.62), rng_for("thoranam"), col))
    bottom = steps[0]
    for sx in (-1, 1):
        stem = P.build_banana_stem(f"Banana_{sx}", 2.2, rng_for("banana", sx), col)
        stem.location = (sx * (bottom.width / 2 + 0.75), bottom.y_front + 0.25, 0)
        stem.rotation_euler = (0, 0, sx * 0.6)
        out.append(stem)
    return out


def place_kuthuvilakku(cfg: GoluConfig, steps: list[StepHandle], col):
    lay = cfg.layout["kuthuvilakku"]
    bottom = steps[0]
    lamps, flames, lights = [], [], []
    for sx in (-1, 1):
        lamp, fl, li = P.build_kuthuvilakku(f"Kuthuvilakku_{'L' if sx < 0 else 'R'}", lay["height"],
                                            rng_for("kuthu", sx), col)
        lamp.location = (sx * (bottom.width / 2 + lay["offset_from_step1_edge"]), bottom.y_front - 0.15, 0)
        lamps.append(lamp)
        flames.extend(fl)
        lights.extend(li)
    return lamps, flames, lights


def _area_light(name: str, size: tuple[float, float], loc, target, kelvin: float, watts: float, col,
                diffuse: float = 1.0, specular: float = 1.0, spread_deg: float = 180.0) -> bpy.types.Object:
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"
    ld.size, ld.size_y = size
    ld.energy = watts
    ld.color = R.kelvin_to_rgb(kelvin)
    ld.diffuse_factor = diffuse
    ld.specular_factor = specular
    if hasattr(ld, "spread"):
        ld.spread = math.radians(spread_deg)
    ob = bpy.data.objects.new(name, ld)
    ob.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return MU.link(ob, col)


def build_lighting(cfg: GoluConfig, col) -> list[bpy.types.Object]:
    P_ = cfg.palette
    tgt = Vector((0.0, -1.2, 1.0))
    # Key: large soft warm area from front-top-left, its spread kept narrow so the walls fall into shadow.
    return [
        _area_light("Key", (3.0, 2.0), (-2.6, -4.2, 3.4), tgt, P_.kelvin("key"), 260, col, spread_deg=55),
        _area_light("Rim_L", (1.2, 0.6), (-1.9, 0.0, 2.95), Vector((-0.6, -1.6, 1.0)), P_.kelvin("rim"), 70, col,
                    0.5, 1.4, spread_deg=70),
        _area_light("Rim_R", (1.2, 0.6), (1.9, 0.0, 2.95), Vector((0.6, -1.6, 1.0)), P_.kelvin("rim"), 70, col,
                    0.5, 1.4, spread_deg=70),
        _area_light("Fill", (2.0, 2.0), (2.8, -3.5, 1.4), tgt, P_.kelvin("fill"), 18, col, spread_deg=90),
    ]


def setup_world(cfg: GoluConfig, scene) -> None:
    R.setup_world_color(scene, cfg.palette.material("world"), 0.35)


def build_environment(cfg: GoluConfig, scene) -> EnvironmentHandles:
    col = MU.ensure_collection("Environment")
    wall_y, front_y = build_room(cfg, col)
    niches = build_niche_wall(cfg, col, wall_y)
    agal_flames = []
    for k, (_, p) in enumerate(niches):
        P.build_agal_vilakku(f"Agal_{k}", p + Vector((0, -0.01, 0.005)), rng_for("agal", k), col, lit=True,
                             size=1.4, power=0.5)
    steps = build_steps(cfg, col)
    for s in steps:
        build_cloth_drape(cfg, s, cfg.step(s.n).cloth_color, col)
        build_brass_trim(s, col)
    build_decorations(cfg, steps, col, wall_y)
    lamps, flames, lights = place_kuthuvilakku(cfg, steps, col)
    lay = cfg.layout["floor_kolam"]
    kol = P.build_kolam("Kolam_Floor", lay["dots"], lay["grid_spacing"], rng_for("kolam"), col,
                        line_width=lay["line_width"], density=lay["mirror_density"], shape=lay["shape"])
    kol.location = (0, steps[0].y_front - lay["distance_from_step1"] - lay["dots"] * lay["grid_spacing"] / 2, 0)
    lights += build_lighting(cfg, col)
    setup_world(cfg, scene)
    return EnvironmentHandles(steps=steps, lamps=lamps, flame_points=flames, lights=lights, collection=col,
                              wall_y=wall_y, front_wall_y=front_y)
