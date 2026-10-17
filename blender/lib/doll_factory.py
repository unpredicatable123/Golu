"""Parametric golu bommai builder (SPEC §4.3, PLAN §3).

make_doll(spec) builds a stylised, hand-painted, varnished clay doll as ONE mesh object in unit space
(figure height = 1) with object scale = real height in metres. Pipeline: skeleton → metaball body →
voxel remesh → painted attributes → garment shells → hair/crown/jewellery → hands & attributes → extras →
vahana → pedestal → join → subdivision + M_ClayGloss.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

from . import attributes as A
from . import materials as M
from . import mesh_utils as MU
from . import vahanas as VH
from .config import MARK_IDS, DollSpec, GoluConfig, Palette, rng_for

V = Vector
HAIR = (0.018, 0.013, 0.011)
GREY_HAIR = (0.55, 0.53, 0.5)
WHITE_HAIR = (0.8, 0.79, 0.76)
K_SKIN, K_GARMENT, K_HAIR, K_GOLD, K_WOOD, K_DETAIL, K_SCALES = 0, 1, 2, 3, 4, 6, 7
MB_SCALE = 1 / 0.67           # metaball element radius per visible radius (threshold 0.6, stiffness 2)

# --------------------------------------------------------------------------- templates


@dataclass(frozen=True)
class Tpl:
    base_cm: float
    head: float
    build: str
    crown: str
    mark: str
    jewellery: str
    hair: str
    head_kind: str = "human"
    lower: str = "legs"
    age: str = "adult"


ARCHETYPES: dict[str, Tpl] = {
    "deity_vishnu_form": Tpl(24, 0.21, "divine-slim", "kireedam", "namam", "divine", "short"),
    "avatar_matsya": Tpl(24, 0.21, "divine-slim", "kireedam", "namam", "divine", "short", lower="fish"),
    "avatar_kurma": Tpl(22, 0.21, "divine-slim", "kireedam", "namam", "divine", "short", lower="tortoise"),
    "avatar_varaha": Tpl(24, 0.21, "divine-broad", "kireedam", "namam", "divine", "short", head_kind="boar"),
    "avatar_narasimha": Tpl(24, 0.22, "divine-broad", "kireedam", "namam", "divine", "short", head_kind="lion"),
    "vamana_vatu": Tpl(24, 0.24, "child", "none", "namam", "none", "short", age="child"),
    "sage_warrior": Tpl(24, 0.20, "athletic", "none", "namam", "simple", "jata"),
    "prince": Tpl(23, 0.21, "slim", "kireedam", "namam", "royal", "short"),
    "king": Tpl(23, 0.21, "portly", "kireedam", "namam", "royal", "short", age="elder"),
    "sage": Tpl(23, 0.21, "lean-elder", "none", "namam", "none", "jata", age="elder"),
    "musician": Tpl(22, 0.21, "average", "none", "vibhuti", "simple", "short"),
    "goddess": Tpl(22, 0.21, "feminine", "karanda_makuta", "tilak_dot", "divine", "kondai"),
    "goddess_consort": Tpl(22, 0.21, "feminine", "karanda_makuta", "tilak_dot", "divine", "kondai"),
    "goddess_warrior": Tpl(22, 0.21, "feminine", "karanda_makuta", "tilak_dot", "divine", "kondai"),
    "deity_murugan": Tpl(23, 0.21, "youthful", "kireedam", "vibhuti", "divine", "short"),
    "deity_ganesha": Tpl(22, 0.24, "stout", "kireedam", "vibhuti", "divine", "short", head_kind="elephant"),
    "tribal_girl": Tpl(21, 0.21, "feminine", "none", "tilak_dot", "simple", "loose_bun"),
    "village_woman": Tpl(21, 0.21, "feminine", "none", "tilak_dot", "simple", "kondai"),
    "village_man": Tpl(22, 0.21, "average", "none", "vibhuti", "none", "short"),
    "chettiar": Tpl(22, 0.21, "stout", "none", "vibhuti", "simple", "receding"),
    "modern_woman": Tpl(21, 0.19, "feminine", "none", "tilak_dot", "simple", "kondai"),
    "modern_man": Tpl(22, 0.19, "average", "none", "none", "none", "short"),
    "schoolchild_girl": Tpl(15, 0.24, "child", "none", "tilak_dot", "none", "braids", age="child"),
    "schoolchild_boy": Tpl(15, 0.24, "child", "none", "none", "none", "short", age="child"),
    "saint_vaishnava": Tpl(22, 0.21, "lean", "none", "namam", "none", "sikha"),
    "saint_andal": Tpl(22, 0.21, "feminine", "none", "namam", "divine", "andal_kondai"),
    "saint_shaiva": Tpl(22, 0.21, "lean", "none", "vibhuti", "none", "shaven"),
    "child_saint": Tpl(22, 0.26, "child", "none", "vibhuti", "none", "short", age="child"),
    "poet_sage": Tpl(22, 0.21, "lean-elder", "none", "none", "none", "hair_knot", age="elder"),
    "elder_woman": Tpl(20, 0.20, "stooped", "none", "vibhuti", "none", "white_bun", age="elder"),
    "infant_krishna": Tpl(22, 0.30, "infant", "none", "namam", "simple", "curls", age="infant"),
    "child_krishna": Tpl(22, 0.24, "child", "none", "namam", "simple", "curls", age="child"),
    "marapachi": Tpl(16, 0.22, "carved", "none", "none", "none", "carved", head_kind="marapachi"),
}


@dataclass(frozen=True)
class Build:
    shoulder: float
    chest: tuple[float, float]
    belly: tuple[float, float]
    hip: float
    arm_r: float
    leg_r: float
    bust: float = 0.0
    slope_deg: float = 22.0


BUILDS: dict[str, Build] = {
    "divine-slim": Build(0.159, (0.124, 0.081), (0.106, 0.081), 0.114, 0.038, 0.046),
    "divine-broad": Build(0.175, (0.140, 0.092), (0.124, 0.092), 0.122, 0.044, 0.050),
    "slim": Build(0.157, (0.121, 0.078), (0.103, 0.078), 0.111, 0.037, 0.045),
    "athletic": Build(0.170, (0.135, 0.086), (0.108, 0.081), 0.114, 0.042, 0.048),
    "portly": Build(0.164, (0.135, 0.092), (0.140, 0.119), 0.122, 0.041, 0.050),
    "average": Build(0.159, (0.124, 0.081), (0.113, 0.086), 0.114, 0.038, 0.046),
    "feminine": Build(0.143, (0.113, 0.081), (0.095, 0.073), 0.127, 0.033, 0.046, bust=0.036, slope_deg=26),
    "youthful": Build(0.157, (0.124, 0.080), (0.104, 0.078), 0.112, 0.038, 0.046),
    "stout": Build(0.175, (0.146, 0.108), (0.178, 0.162), 0.138, 0.049, 0.05),
    "lean": Build(0.151, (0.108, 0.073), (0.095, 0.071), 0.106, 0.035, 0.042),
    "lean-elder": Build(0.151, (0.108, 0.076), (0.099, 0.076), 0.106, 0.035, 0.042),
    "child": Build(0.143, (0.119, 0.086), (0.117, 0.092), 0.111, 0.041, 0.050, slope_deg=18),
    "infant": Build(0.138, (0.124, 0.097), (0.130, 0.108), 0.117, 0.051, 0.058, slope_deg=12),
    "stooped": Build(0.138, (0.108, 0.081), (0.097, 0.076), 0.119, 0.032, 0.042, bust=0.02, slope_deg=30),
    "carved": Build(0.127, (0.108, 0.092), (0.108, 0.092), 0.111, 0.038, 0.050, slope_deg=30),
}

# pose → (legs type, seat height of pelvis above base, forward lean (rad), hip sway)
POSES: dict[str, tuple[str, float, float, float]] = {
    "standing": ("straight", 0, 0, 0), "standing_rigid": ("rigid", 0, 0, 0),
    "standing_tribhanga": ("tribhanga", 0, 0, 0.022), "standing_crossed_legs": ("crossed", 0, 0, 0.015),
    "standing_lifted_knee": ("lifted_knee", 0, 0.05, 0), "standing_offering": ("straight", 0, 0, 0),
    "standing_playing": ("straight", 0, 0.04, 0), "standing_slinging": ("tribhanga", 0, 0, -0.02),
    "standing_lifting": ("straight", 0, 0, 0.015), "standing_stooped": ("stooped", 0, 0.32, 0),
    "seated_throne": ("pendant", 0.21, 0, 0), "seated_lalitasana": ("lalitasana", 0.21, 0, 0),
    "seated_padmasana": ("folded", 0.075, 0, 0), "seated_cross_legged": ("folded", 0.075, 0, 0),
    "seated_floor": ("folded", 0.06, 0, 0), "seated_veena": ("folded", 0.09, 0, 0),
    "seated_writing": ("folded", 0.075, 0.08, 0), "seated_churning": ("folded", 0.075, 0.12, 0),
    "seated_squat_vending": ("squat", 0.13, 0.25, 0), "seated_squat_wheel": ("squat", 0.13, 0.3, 0),
    "seated_cart": ("pendant", 0.2, 0, 0), "bending_kolam": ("bend", 0, 0.95, 0),
    "crawling": ("crawl", 0, 1.25, 0), "dancing_child": ("dance_lift", 0, 0, 0.02),
    "dancing_one_leg": ("dance_one_leg", 0, 0, -0.02), "riding": ("pendant", 0.0, 0, 0),
    "upright_tail": ("none", 0, 0, 0), "upright_shell": ("none", -0.22, 0, 0),
}

TWO_HANDED = {"veena", "flute", "garland", "nadaswaram", "churning_rope", "laptop", "potters_wheel"}
SEAT_RAISED = {"lotus_seat", "white_lotus_seat", "peetam", "pillar_throne"}


# --------------------------------------------------------------------------- data


@dataclass
class Params:
    spec: DollSpec
    tpl: Tpl
    build: Build
    H: float
    rng: random.Random
    pal: Palette
    cfg: GoluConfig
    crown: str
    hair: str
    jewellery: str
    mark: str
    legs: str
    seat_h: float
    lean: float
    sway: float


@dataclass
class Arm:
    side: int              # −1 doll's right (−X), +1 doll's left (+X)
    pair: int
    token: str
    shoulder: V
    elbow: V = None
    wrist: V = None
    hand_dir: V = None     # direction from wrist to fingertips
    palm: V = None         # palm normal
    grip_up: V = None      # axis for a held item


@dataclass
class Skel:
    hh: float
    rx: float
    ry: float
    rz: float
    head_c: V
    z_sh: float
    z_ch: float
    z_bl: float
    z_hp: float
    hip_x: float
    legs: list[list[V]] = field(default_factory=list)
    arms: list[Arm] = field(default_factory=list)
    pivot: V = None
    lean: float = 0.0
    items: list[tuple[str, Matrix]] = field(default_factory=list)

    def lean_mat(self) -> Matrix:
        if not self.lean:
            return Matrix.Identity(4)
        return Matrix.Translation(self.pivot) @ Matrix.Rotation(self.lean, 4, "X") @ Matrix.Translation(-self.pivot)

    def up(self, p) -> V:
        """Transform an upright upper-body point into the posed (leaning) frame."""
        return self.lean_mat() @ V(p)

    def updir(self, d) -> V:
        return (self.lean_mat().to_3x3() @ V(d)).normalized()


# =========================================================================== params & skeleton


def resolve_params(spec: DollSpec, cfg: GoluConfig) -> Params:
    tpl = ARCHETYPES[spec.archetype]
    ex = set(spec.extras)
    crown = tpl.crown
    for c in ("kireedam", "karanda_makuta", "peacock_feather_crown", "turban_cloth"):
        if c in ex:
            crown = c
    hair = tpl.hair
    for h in ("kudumi", "sikha", "jata", "hair_knot", "white_hair_bun", "andal_kondai", "braids"):
        if h in ex:
            hair = {"white_hair_bun": "white_bun"}.get(h, h)
    if "shaven_head" in ex:
        hair = "shaven"
    jew = tpl.jewellery
    if "bridal_jewellery" in ex:
        jew = "divine"
    elif "royal_jewellery" in ex and jew in ("none", "simple"):
        jew = "royal"
    legs, seat, lean, sway = POSES.get(spec.pose, POSES["standing"])
    if tpl.head_kind == "elephant" and legs in ("pendant", "lalitasana"):
        seat = 0.16
    if spec.seat not in SEAT_RAISED and legs in ("pendant", "lalitasana") and spec.pose != "riding":
        seat = max(seat, 0.2)
    if spec.seat in SEAT_RAISED and legs == "folded":
        seat = 0.12
    return Params(spec=spec, tpl=tpl, build=BUILDS[tpl.build], H=tpl.base_cm * spec.scale / 100.0,
                  rng=rng_for("doll", spec.id), pal=cfg.palette, cfg=cfg, crown=crown, hair=hair,
                  jewellery=jew, mark=spec.forehead or tpl.mark, legs=legs, seat_h=seat, lean=lean, sway=sway)


def build_skeleton(p: Params) -> Skel:
    hh = p.tpl.head
    rz = hh * 0.5
    rx, ry = hh * 0.43, hh * 0.45
    if p.tpl.head_kind == "elephant":
        rx, ry, rz = hh * 0.56, hh * 0.55, hh * 0.55
    child = p.tpl.age in ("child", "infant")
    z_top = 1.0
    z_sh_stand = z_top - hh - (0.012 if not child else 0.008)
    z_hp_stand = z_sh_stand - (0.29 if not child else 0.25)
    if p.tpl.age == "infant":
        z_hp_stand = z_sh_stand - 0.22
    # seated: pelvis rests at seat_h + leg thickness; whole upper body shifts down
    seated = p.legs in ("folded", "pendant", "lalitasana", "squat")
    if seated:
        z_hp = p.seat_h + p.build.leg_r * 1.1
    elif p.legs == "none":
        z_hp = z_hp_stand + p.seat_h
    else:
        z_hp = z_hp_stand
    shift = z_hp - z_hp_stand
    z_sh = z_sh_stand + shift
    head_c = V((0.0, 0.004, z_top - rz + shift))
    sk = Skel(hh=hh, rx=rx, ry=ry, rz=rz, head_c=head_c, z_sh=z_sh, z_ch=z_sh - 0.075, z_bl=z_sh - 0.19,
              z_hp=z_hp, hip_x=p.sway)
    sk.pivot = V((p.sway, 0.0, z_hp))
    sk.lean = p.lean
    sk.legs = _legs(p, sk)
    return sk


def _legs(p: Params, sk: Skel) -> list[list[V]]:
    hx = p.build.hip * 0.55
    z = sk.z_hp
    sw = sk.hip_x
    out = []
    L = p.legs
    if L == "none":
        return out
    knee_z, ank_z = z * 0.53, 0.045
    short = 0.72 if p.tpl.build == "stout" and p.tpl.head_kind == "elephant" else 1.0
    for s in (-1, 1):
        hip = V((sw + s * hx, 0.0, z))
        if L in ("straight", "rigid", "stooped", "bend"):
            bend = 0.03 if L in ("stooped", "bend") else 0.0
            knee = V((s * hx * 1.05, -0.01 - bend, knee_z))
            ank = V((s * hx * 1.05, 0.0, ank_z))
        elif L == "tribhanga":
            if s > 0:
                knee = V((s * hx * 0.7, -0.035, knee_z)); ank = V((s * hx * 0.5, 0.0, ank_z))
            else:
                knee = V((s * hx * 1.1, -0.005, knee_z)); ank = V((s * hx * 1.1, 0.0, ank_z))
        elif L == "crossed":
            if s < 0:
                knee = V((0.0, -0.035, knee_z)); ank = V((hx * 1.3, -0.045, ank_z + 0.02))
            else:
                knee = V((hx, -0.005, knee_z)); ank = V((hx, 0.0, ank_z))
        elif L == "lifted_knee":
            if s > 0:
                knee = V((hx * 1.3, -0.15, z * 0.72)); ank = V((hx * 1.3, -0.17, 0.16))
            else:
                knee = V((s * hx, -0.005, knee_z)); ank = V((s * hx, 0.0, ank_z))
        elif L == "dance_lift":
            if s > 0:
                knee = V((hx * 1.9, -0.1, z * 0.75)); ank = V((hx * 1.2, -0.02, z * 0.42))
            else:
                knee = V((s * hx, -0.01, knee_z)); ank = V((s * hx, 0.0, ank_z))
        elif L == "dance_one_leg":
            if s < 0:
                knee = V((s * hx * 2.6, -0.12, z * 0.92)); ank = V((s * hx * 1.6, -0.08, z * 0.62))
            else:
                knee = V((s * hx * 0.9, -0.01, knee_z)); ank = V((s * hx * 0.9, 0.0, ank_z))
        elif L == "folded":
            knee = V((s * 0.17, -0.13, z - 0.03))
            ank = V((-s * 0.07, -0.16, z - 0.025))
        elif L == "pendant" or (L == "lalitasana" and s < 0):
            knee = V((s * hx * 1.25, -0.16 * short, z - 0.01))
            ank = V((s * hx * 1.3, -0.18 * short, max(z - 0.24 * short, 0.04)))
        elif L == "lalitasana":
            knee = V((s * 0.17 * short, -0.14 * short, z - 0.03))
            ank = V((-0.02, -0.13 * short, z - 0.03))
        elif L == "squat":
            knee = V((s * 0.11, -0.13, z + 0.12))
            ank = V((s * 0.085, -0.05, 0.045))
            hip = V((sw + s * hx, 0.04, z))
        elif L == "crawl":
            knee = V((s * hx, -0.02, 0.04))
            ank = V((s * hx, 0.2, 0.035))
            hip = V((s * hx, 0.0, z * 0.45))
        else:
            raise KeyError(f"legs type {L}")
        toe = ank + V((0.0, -0.065, -0.02)) if L not in ("crawl",) else ank + V((0, 0.05, -0.01))
        if L == "folded":
            toe = ank + V((s * 0.04, 0.02, 0.0))
        out.append([hip, knee, ank, toe])
    return out


# --------------------------------------------------------------------------- arms


def _ik(shoulder: V, wrist: V, upper: float, fore: float, pole: V) -> tuple[V, V]:
    d = wrist - shoulder
    dist = min(max(d.length, 1e-4), (upper + fore) * 0.999)
    dn = d.normalized()
    wrist = shoulder + dn * dist
    a = (upper * upper - fore * fore + dist * dist) / (2 * dist)
    h = math.sqrt(max(upper * upper - a * a, 0.0))
    pole_perp = (pole - dn * pole.dot(dn))
    if pole_perp.length < 1e-6:
        pole_perp = V((0, 0, -1))
    elbow = shoulder + dn * a + pole_perp.normalized() * h
    return elbow, wrist


def _hand_target(token: str, s: int, sk: Skel, p: Params) -> tuple[V, V, V]:
    """(wrist, hand_dir, palm) in the upright body frame for front-pair tokens."""
    zc, zh, zs = sk.z_ch, sk.z_hp, sk.z_sh
    sw = p.build.shoulder
    fwd = V((0, -1, 0))
    T = {
        "abhaya": (V((s * (sw + 0.035), -0.085, zc - 0.03)), V((0, -0.15, 1)), fwd),
        "abhaya_coins": (V((s * (sw + 0.035), -0.085, zc - 0.03)), V((0, -0.15, 1)), fwd),
        "varada": (V((s * (sw + 0.04), -0.08, zh + 0.04)), V((s * 0.1, -0.35, -1)), fwd),
        "varada_coins": (V((s * (sw + 0.04), -0.08, zh + 0.04)), V((s * 0.1, -0.35, -1)), fwd),
        "kati": (V((s * (p.build.hip + 0.02), -0.02, zh + 0.035)), V((-s, -0.2, -0.5)), V((s, 0, 0))),
        "anjali": (V((s * 0.022, -p.build.chest[1] - 0.06, zc - 0.005)), V((0, -0.1, 1)), V((-s, 0, 0))),
        "lola": (V((s * (sw + 0.045), 0.0, zh - 0.01)), V((0, 0, -1)), V((-s, 0, 0))),
        "chin": (V((s * 0.065, -p.build.chest[1] - 0.055, zc + 0.0)), V((-s * 0.3, -0.2, 1)), fwd),
        "hridaya": (V((s * 0.04, -p.build.chest[1] - 0.03, zc - 0.03)), V((-s, -0.1, 0.4)), V((0, 1, 0))),
        "point_up": (V((s * (sw + 0.02), -0.05, zs + 0.14)), V((0, 0, 1)), fwd),
        "point": (V((s * (sw - 0.02), -0.15, zc - 0.03)), V((s * 0.3, -1, 0.2)), V((0, 0, -1))),
        "serpent_tail": (V((s * (sw + 0.07), -0.05, zc + 0.02)), V((s, 0, 0)), fwd),
        "lift_hill_finger": (V((s * 0.09, -0.02, 1.0 + 0.05)), V((0, 0, 1)), fwd),
        "pot_on_head_hold": (V((s * 0.11, 0.0, 0.98)), V((-s * 0.3, 0, 1)), V((-s, 0, 0))),
        "kolam_pinch": (V((s * 0.09, -0.24, zh - 0.12)), V((0, -0.3, -1)), V((0, 0, -1))),
        "thavil_thimble": (V((s * (p.build.belly[0] + 0.08), -0.06, zh + 0.03)), V((-s, -0.3, 0)), V((-s, 0, 0))),
    }
    if token in T:
        w, d, n = T[token]
        return w, d.normalized(), n.normalized()
    # generic held emblem in the front hand
    return V((s * (sw + 0.04), -0.095, zc - 0.07)), V((0, -0.2, 1)).normalized(), V((-s, 0, 0))


def _arms(p: Params, sk: Skel) -> list[Arm]:
    n = p.spec.arms
    toks = list(p.spec.attributes)
    if n == 0:
        return []
    sw = p.build.shoulder
    slope = math.radians(p.build.slope_deg)
    child = p.tpl.age in ("child", "infant")
    upper = 0.17 if not child else 0.14
    fore = 0.15 if not child else 0.12
    pairs = n // 2
    arms: list[Arm] = []
    # two-handed items occupying the front pair
    front_two = toks[0] if len(toks) >= 2 and toks[0] == toks[1] and toks[0] in TWO_HANDED else None
    grips: dict[int, V] = {}
    if front_two:
        frame = _body_item_frame(front_two, p, sk)
        sk.items.append((front_two, frame))
        for side, gp in _item_grips(front_two).items():
            grips[side] = frame @ gp
    for pr in range(pairs):
        for side_i, s in enumerate((-1, 1)):
            tok = toks[pr * 2 + side_i]
            sh = V((s * sw * 0.96, 0.006, sk.z_sh - math.tan(slope) * sw * 0.3))
            if pr == 0:
                if front_two:
                    wrist = grips[s]
                    hand_dir = V((0, -0.3, 1)).normalized()
                    palm = V((-s, 0, 0))
                else:
                    wrist, hand_dir, palm = _hand_target(tok, s, sk, p)
                pole = V((s * 0.6, 0.35, -1.0))
                shoulder = sh
            else:
                nb = pairs - 1
                t = 0.5 if nb == 1 else (pr - 1) / (nb - 1)
                lo, hi = (math.radians(-12), math.radians(68)) if nb >= 3 else (math.radians(8), math.radians(58))
                theta = lo + (hi - lo) * t if nb > 1 else math.radians(38)
                shoulder = sh + V((s * -0.012, 0.018 + 0.006 * pr, 0.012))
                reach = (upper + fore) * (0.86 - 0.06 * (pr - 1))
                dirv = V((s * math.cos(theta), 0.12 + 0.05 * pr, math.sin(theta))).normalized()
                wrist = shoulder + dirv * reach
                hand_dir = V((s * 0.15, -0.1, 1)).normalized()
                palm = V((0, -1, 0))
                pole = V((s * 0.4, 0.6, -0.8))
            scale = 1.0 if pr == 0 else 0.92 ** pr
            elbow, wrist = _ik(shoulder, wrist, upper * scale, fore * scale, pole)
            arm = Arm(side=s, pair=pr, token=tok, shoulder=sk.up(shoulder), elbow=sk.up(elbow), wrist=sk.up(wrist),
                      hand_dir=sk.updir(hand_dir), palm=sk.updir(palm))
            arm.grip_up = sk.updir(V((s * 0.12, 0, 1)) if not tok.endswith("coins") else V((0, 0, 1)))
            arms.append(arm)
    return arms


def _body_item_frame(token: str, p: Params, sk: Skel) -> Matrix:
    """Placement of two-handed items relative to the body (upright frame; lean applied later)."""
    zc, zh = sk.z_ch, sk.z_hp
    mouth = V((0, -sk.ry * 0.9, sk.head_c.z - sk.rz * 0.45))
    if token == "veena":
        rot = Matrix.Rotation(math.radians(-30), 4, "Y") @ Matrix.Rotation(math.radians(-90), 4, "X")
        return Matrix.Translation(V((-0.16, -0.16, zh + 0.03))) @ rot @ Matrix.Scale(0.62, 4)
    if token == "flute":
        rot = Matrix.Rotation(math.radians(8), 4, "Z") @ Matrix.Rotation(math.radians(-12), 4, "Y")
        return Matrix.Translation(mouth + V((-0.115, -0.03, -0.012))) @ rot
    if token == "garland":
        return Matrix.Translation(V((0, -p.build.chest[1] - 0.09, zc + 0.07)))
    if token == "nadaswaram":
        d = V((0.0, -0.55, -1.0)).normalized()
        rot = V((0, 0, 1)).rotation_difference(d).to_matrix().to_4x4()
        return Matrix.Translation(mouth + V((0, -0.01, 0))) @ rot
    if token == "churning_rope":
        return Matrix.Translation(V((0, -0.2, zc - 0.02)))
    if token == "laptop":
        return Matrix.Translation(V((0, -0.14, zh + 0.03)))
    if token == "potters_wheel":
        return Matrix.Translation(V((0, -0.26, 0.0)))
    return Matrix.Identity(4)


def _item_grips(token: str) -> dict[int, V]:
    return {
        "veena": {-1: V((0.04, -0.07, 0.07)), 1: V((0.3, -0.02, 0.08))},
        "flute": {-1: V((-0.05, 0.0, -0.012)), 1: V((0.04, 0.0, -0.012))},
        "garland": {-1: V((-0.075, 0.0, -0.03)), 1: V((0.075, 0.0, -0.03))},
        "nadaswaram": {-1: V((0.0, -0.012, 0.13)), 1: V((0.0, -0.012, 0.22))},
        "churning_rope": {-1: V((-0.05, -0.02, 0.06)), 1: V((0.05, -0.02, 0.06))},
        "laptop": {-1: V((-0.03, -0.02, 0.01)), 1: V((0.03, -0.02, 0.01))},
        "potters_wheel": {-1: V((-0.04, 0.0, 0.055)), 1: V((0.04, 0.0, 0.055))},
    }[token]


# =========================================================================== body


def _ell(co, vis_r, size=(1, 1, 1), rot=None, neg=False):
    e = MU.MetaElem("ELLIPSOID", co, vis_r * MB_SCALE, size, rot)
    e.negative = neg
    return e


def _cap(a, b, vis_r):
    return MU.capsule_between(V(a), V(b), vis_r * MB_SCALE)


def _ball(co, vis_r):
    return MU.MetaElem("BALL", co, vis_r * MB_SCALE)


def body_elements(p: Params, sk: Skel) -> list[MU.MetaElem]:
    b = p.build
    els: list[MU.MetaElem] = []
    up = sk.up
    hk = p.tpl.head_kind
    hc = sk.head_c
    child = p.tpl.age in ("child", "infant")
    # head
    if hk in ("human", "marapachi", "lion", "boar"):
        els.append(_ell(up(hc), sk.rz, (sk.rx / sk.rz, sk.ry / sk.rz, 1.0)))
        if hk in ("human", "marapachi"):
            els.append(_ell(up(hc + V((0, -sk.ry * 0.18, -sk.rz * 0.38))), sk.rz * 0.72, (0.95, 0.85, 0.75)))
            els.append(_ell(up(hc + V((0, -sk.ry * 0.95, -sk.rz * 0.12))), sk.rz * 0.13, (0.75, 1.0, 1.25)))
            for s in (-1, 1):
                els.append(_ell(up(hc + V((s * sk.rx * 0.98, 0.04 * sk.ry, -0.08 * sk.rz))), sk.rz * 0.2,
                                (0.45, 0.8, 1.0)))
    elif hk == "elephant":
        rz = sk.rz
        els.append(_ell(up(hc), rz, (sk.rx / rz, sk.ry / rz, 1.0)))
        for s in (-1, 1):
            els.append(_ball(up(hc + V((s * 0.36 * rz, -0.48 * rz, 0.55 * rz))), 0.42 * rz))
            els.append(_ell(up(hc + V((s * 0.42 * rz, -0.62 * rz, -0.35 * rz))), 0.38 * rz, (1, 0.8, 0.9)))
        pts = [hc + V((0, -0.92 * rz, -0.25 * rz)), hc + V((0, -1.08 * rz, -0.75 * rz)),
               hc + V((0.04 * rz, -1.12 * rz, -1.3 * rz)), hc + V((0.32 * rz, -1.08 * rz, -1.75 * rz)),
               hc + V((0.62 * rz, -0.98 * rz, -1.78 * rz)), hc + V((0.78 * rz, -0.95 * rz, -1.55 * rz))]
        radii = [0.34, 0.29, 0.24, 0.19, 0.15, 0.12]
        for i in range(len(pts) - 1):
            els.append(_cap(up(pts[i]), up(pts[i + 1]), radii[i] * rz))
    # neck
    neck_top = hc - V((0, 0, sk.rz * 0.72))
    els.append(_cap(up(neck_top), up(V((0, 0.004, sk.z_sh + 0.01))), 0.048 if not child else 0.05))
    # shoulders (sloped)
    slope = math.radians(b.slope_deg)
    for s in (-1, 1):
        a = V((0, 0.004, sk.z_sh + 0.008))
        sh = V((s * b.shoulder * 0.96, 0.006, sk.z_sh - math.tan(slope) * b.shoulder * 0.3))
        els.append(_cap(up(a), up(sh), b.arm_r * 1.45))
    # torso
    els.append(_ell(up(V((0, 0.0, sk.z_ch))), b.chest[0], (1.0, b.chest[1] / b.chest[0], 0.9)))
    if b.bust:
        for s in (-1, 1):
            els.append(_ball(up(V((s * 0.045, -b.chest[1] * 0.72, sk.z_ch - 0.01))), b.bust))
    belly_y = -0.02 if b.belly[1] > 0.1 or "pot_belly" in p.spec.extras else 0.0
    bel = b.belly if "pot_belly" not in p.spec.extras else (b.belly[0] * 1.08, b.belly[1] * 1.25)
    els.append(_ell(up(V((0, belly_y, sk.z_bl))), bel[0], (1.0, bel[1] / bel[0], 0.95)))
    if p.tpl.lower == "legs" or p.legs != "none":
        els.append(_ell(V((sk.hip_x, 0.0, sk.z_hp + 0.03)), b.hip, (1.0, 0.72, 0.65)))
    # legs
    for leg in sk.legs:
        hip, knee, ank, toe = leg
        els.append(_cap(hip, knee, b.leg_r))
        els.append(_cap(knee, ank, b.leg_r * 0.72))
        els.append(_cap(ank, toe, b.leg_r * 0.55))
    # arms
    for arm in sk.arms:
        sc = 1.0 if arm.pair == 0 else 0.9
        els.append(_cap(arm.shoulder, arm.elbow, b.arm_r * sc))
        els.append(_cap(arm.elbow, arm.wrist, b.arm_r * 0.8 * sc))
        tip = arm.wrist + arm.hand_dir * 0.032
        els.append(_cap(arm.wrist, tip, b.arm_r * 0.75 * sc))
        if arm.token in ("point_up", "point", "lift_hill_finger"):
            els.append(_cap(tip, tip + arm.hand_dir * 0.035, b.arm_r * 0.22))
    # lower-body specials
    if p.tpl.lower == "fish":
        z = sk.z_hp
        pts = [V((0, 0.0, z + 0.04)), V((0.0, 0.02, z - 0.12)), V((0.05, 0.04, z - 0.27)), V((0.13, 0.03, z - 0.37)),
               V((0.22, 0.0, z - 0.4))]
        rr = [0.11, 0.105, 0.08, 0.055, 0.035]
        for i in range(len(pts) - 1):
            els.append(_cap(pts[i], pts[i + 1], rr[i]))
    if "beard" in p.spec.extras:
        els.append(_ell(up(hc + V((0, -sk.ry * 0.62, -sk.rz * 0.95))), sk.rz * 0.55, (0.95, 0.7, 1.25)))
    return els


def build_body(p: Params, sk: Skel) -> bpy.types.Object:
    els = body_elements(p, sk)
    mb = MU.metaball_object(f"mb_{p.spec.id}", els, 0.0055)
    body = MU.metaball_to_mesh(mb, f"{p.spec.id}_body")
    MU.voxel_remesh(body, 1 / 175, smooth_iters=3)
    skin = p.pal.skin(p.spec.skin)
    kind = K_WOOD if p.spec.skin == "red-sanders" else K_SKIN
    MU.set_part_attributes(body, skin, 0.0, 0.42 if kind == K_SKIN else 0.35, kind)
    _paint_body(p, sk, body)
    return body


def _paint_body(p: Params, sk: Skel, body) -> None:
    """Hair, beard, blouse/shirt, special-head colours and lower-body scales on the body mesh."""
    hc = sk.up(sk.head_c)
    lm = sk.lean_mat().inverted()
    hair = p.hair
    hair_col = WHITE_HAIR if hair == "white_bun" else (GREY_HAIR if p.tpl.age == "elder" and hair == "jata" else HAIR)
    att = p.spec.attire
    upper = att.upper if att else "bare"
    lower = att.lower if att else "none"
    blouse_col = p.pal.silk(att.accent) if att else None
    shirt_col = p.pal.silk(att.color) if att else None
    hk = p.tpl.head_kind
    lion_col = p.pal.silk("turmeric")
    b = p.build

    def fn(co, n):
        c = lm @ co
        rel = c - sk.head_c
        xn, yn, zn = rel.x / sk.rx, rel.y / sk.ry, rel.z / sk.rz
        in_head = xn * xn + yn * yn + zn * zn < 1.45 ** 2 and c.z > sk.z_sh + 0.02
        if in_head:
            if hk == "lion":
                return (lion_col, 0.0, 0.42, K_SKIN)
            if "beard" in p.spec.extras:
                br = (c - (sk.head_c + V((0, -sk.ry * 0.62, -sk.rz * 0.95))))
                if (br.x / 0.95) ** 2 + (br.y / 0.7) ** 2 + (br.z / 1.25) ** 2 < (sk.rz * 0.62) ** 2 and zn < -0.25:
                    return (hair_col if p.tpl.age != "elder" else WHITE_HAIR, 0.0, 0.55, K_HAIR)
            if hk in ("human", "marapachi") and hair not in ("shaven",):
                if hair == "receding":
                    t = 0.62 + 0.15 * (-yn)
                elif yn < 0:
                    t = 0.02 + 0.42 * yn * yn
                else:
                    t = 0.02 - 0.75 * yn
                if zn > t and hk == "human":
                    return (hair_col, 0.0, 0.5, K_HAIR)
                if hk == "marapachi" and zn > 0.45:
                    return ((0.05, 0.02, 0.015), 0.0, 0.4, K_WOOD)
            return None
        if p.tpl.lower == "fish" and c.z < sk.z_hp + 0.03:
            return (p.pal.silk("peacock-blue"), 0.15, 0.3, K_SCALES)
        torso = sk.z_hp + 0.05 < c.z < sk.z_sh + 0.035
        arm_upper = abs(c.x) > b.chest[0] * 0.9 and c.z > sk.z_ch - 0.12
        if upper in ("blouse", "half_saree") and blouse_col is not None:
            neck_open = c.z > sk.z_ch + 0.02 and abs(c.x) < 0.055 and c.y < 0
            midriff = sk.z_hp + 0.05 < c.z < sk.z_ch - 0.075 and lower in ("saree", "half_saree")
            if torso and not neck_open and not midriff and (abs(c.x) < b.chest[0] * 1.35 or c.z > sk.z_ch - 0.04):
                return (blouse_col, 0.0, 0.38, K_GARMENT)
        if upper in ("shirt", "lab_coat") and shirt_col is not None:
            if c.z > sk.z_hp - 0.01 and c.z < sk.z_sh + 0.05 and not (c.z > sk.z_ch + 0.035 and abs(c.x) < 0.035 and c.y < 0):
                return (shirt_col, 0.0, 0.45, K_GARMENT)
            if abs(c.x) > b.chest[0] * 0.95 and c.z > sk.z_hp - 0.05:
                return (shirt_col, 0.0, 0.45, K_GARMENT)
        if lower in ("trousers", "shorts") and c.z < sk.z_hp + 0.05 and abs(c.x) < 0.2:
            limit = 0.0 if lower == "trousers" else sk.z_hp * 0.5
            if c.z > limit:
                return (p.pal.silk(att.accent), 0.0, 0.45, K_GARMENT)
        return None
    MU.paint_corners(body, fn)


# =========================================================================== special heads & lower bodies


def special_head_parts(p: Params, sk: Skel, P: A.Paint) -> list[bpy.types.Object]:
    hk = p.tpl.head_kind
    hc = sk.up(sk.head_c)
    rz = sk.rz
    out = []
    if hk == "elephant":
        grey = p.pal.skin(p.spec.skin)
        for s in (-1, 1):
            ear = MU.uv_sphere(f"{p.spec.id}_ear{s}", rz * 0.95, 18, 10, scale=(0.14, 1.0, 1.15))
            A._place(ear, hc + V((s * 1.02 * rz, 0.18 * rz, -0.08 * rz)), (0, 0, s * 0.35))
            P.col(ear, grey, 0.42, kind=K_DETAIL)
            MU.paint_corners(ear, lambda co, n, s=s: (p.pal.silk("lotus-pink"), 0.0, 0.45, K_DETAIL)
                             if co.y < hc.y + 0.12 * rz and abs(co.x - (hc.x + s * 1.02 * rz)) < rz * 0.2 and
                             ((co.z - hc.z) ** 2 + (co.y - hc.y - 0.18 * rz) ** 2) < (rz * 0.75) ** 2 else None)
            out.append(ear)
        # left tusk (doll's left, +X) whole; right tusk broken — its piece is held in R1 (D11)
        lt = MU.tube(f"{p.spec.id}_tuskL", [hc + V((0.34 * rz, -0.9 * rz, -0.62 * rz)),
                                             hc + V((0.46 * rz, -1.2 * rz, -0.92 * rz)),
                                             hc + V((0.42 * rz, -1.36 * rz, -0.66 * rz))], 0.1 * rz,
                     radii=[1, 0.75, 0.25])
        rt = MU.tube(f"{p.spec.id}_tuskR", [hc + V((-0.34 * rz, -0.9 * rz, -0.62 * rz)),
                                             hc + V((-0.4 * rz, -1.04 * rz, -0.75 * rz))], 0.1 * rz, radii=[1, 0.9])
        out += [P.col(lt, p.pal.silk("ivory"), 0.3), P.col(rt, p.pal.silk("ivory"), 0.3)]
    elif hk == "lion":
        gold = p.pal.silk("turmeric")
        muz = MU.uv_sphere(f"{p.spec.id}_muz", rz * 0.55, 14, 8, scale=(1.15, 0.9, 0.75))
        A._place(muz, hc + V((0, -0.85 * rz, -0.38 * rz)))
        mouth = MU.uv_sphere(f"{p.spec.id}_mouth", rz * 0.36, 12, 8, scale=(1.15, 0.6, 0.75))
        A._place(mouth, hc + V((0, -1.12 * rz, -0.66 * rz)))
        nose = MU.uv_sphere(f"{p.spec.id}_nose", rz * 0.15, 10, 6, scale=(1.3, 1, 0.8))
        A._place(nose, hc + V((0, -1.3 * rz, -0.25 * rz)))
        out += [P.col(muz, gold, 0.42, kind=K_DETAIL), P.col(mouth, p.pal.silk("kumkum"), 0.3, kind=K_DETAIL),
                P.col(nose, (0.05, 0.02, 0.02), 0.3, kind=K_DETAIL)]
        for s in (-1, 1):
            fang = MU.cylinder(f"{p.spec.id}_fang{s}", rz * 0.05, rz * 0.2, 6, radius_top=0.0)
            A._place(fang, hc + V((s * 0.18 * rz, -1.3 * rz, -0.5 * rz)), (math.pi, 0, 0))
            out.append(P.col(fang, p.pal.silk("white"), 0.3, kind=K_DETAIL))
        # mane: three rings of pointed flame-like tufts radiating from the face (golu lion style)
        for ring in range(3):
            n = 22 + ring * 6
            for i in range(n):
                a = i / n * math.tau + ring * 0.12
                r = rz * (0.95 + ring * 0.24)
                pos = hc + V((math.cos(a) * r, 0.2 * rz + ring * 0.1 * rz, math.sin(a) * r * 1.05 + 0.1 * rz))
                if pos.z < hc.z - 1.25 * rz:
                    continue
                t = MU.cylinder(f"{p.spec.id}_mane{ring}_{i}", rz * (0.2 - ring * 0.03), rz * (0.55 + ring * 0.08), 8,
                                radius_top=0.0)
                t.scale = (1.0, 0.55, 1.0)
                MU.apply_transform(t)
                tip_dir = V((math.cos(a), 0.15, math.sin(a))).normalized()
                rot = V((0, 0, 1)).rotation_difference(tip_dir).to_euler()
                A._place(t, pos + tip_dir * rz * 0.22, rot)
                colr = (p.pal.silk("saffron"), gold, p.pal.material("flame-base"))[ring]
                out.append(P.col(t, colr, 0.45, kind=K_DETAIL))
    elif hk == "boar":
        blue = p.pal.skin(p.spec.skin)
        snout = MU.tube(f"{p.spec.id}_snout", [hc + V((0, -0.6 * rz, -0.15 * rz)), hc + V((0, -1.25 * rz, -0.35 * rz)),
                                                hc + V((0, -1.65 * rz, -0.42 * rz))], 0.42 * rz, radii=[1, 0.75, 0.55])
        disc = MU.cylinder(f"{p.spec.id}_disc", 0.25 * rz, 0.06 * rz, 16)
        A._place(disc, hc + V((0, -1.75 * rz, -0.42 * rz)), (math.pi / 2, 0, 0))
        out += [P.col(snout, blue, 0.42, kind=K_DETAIL), P.col(disc, p.pal.silk("lotus-pink"), 0.4, kind=K_DETAIL)]
        for s in (-1, 1):
            tusk = MU.tube(f"{p.spec.id}_btusk{s}", [hc + V((s * 0.3 * rz, -1.3 * rz, -0.55 * rz)),
                                                    hc + V((s * 0.42 * rz, -1.45 * rz, -0.35 * rz)),
                                                    hc + V((s * 0.36 * rz, -1.45 * rz, -0.12 * rz))], 0.07 * rz,
                           radii=[1, 0.7, 0.2])
            ear = A.leaf_shell(f"{p.spec.id}_bear{s}", 0.55 * rz, 0.35 * rz, cup=0.4)
            A._place(ear, hc + V((s * 0.6 * rz, 0.1 * rz, 0.6 * rz)), (0.3, s * 0.6, 0))
            out += [P.col(tusk, p.pal.silk("ivory"), 0.3, kind=K_DETAIL), P.col(ear, blue, 0.42, kind=K_DETAIL)]
    return out


def lower_body_parts(p: Params, sk: Skel, P: A.Paint) -> list[bpy.types.Object]:
    out = []
    if p.tpl.lower == "fish":
        z = sk.z_hp
        tip = V((0.22, 0.0, z - 0.4))
        for s in (-1, 1):
            fin = A.leaf_shell(f"{p.spec.id}_fin{s}", 0.13, 0.07, cup=0.1)
            A._place(fin, tip, (0, math.radians(60 + s * 40), 0))
            MU.set_part_attributes(fin, p.pal.silk("peacock-blue"), 0.2, 0.3, K_SCALES)
            out.append(fin)
        dfin = A.leaf_shell(f"{p.spec.id}_dfin", 0.12, 0.05, cup=0.0)
        A._place(dfin, V((0.04, 0.07, z - 0.2)), (math.radians(-60), 0, 0))
        MU.set_part_attributes(dfin, p.pal.silk("peacock-blue"), 0.2, 0.3, K_SCALES)
        out.append(dfin)
    elif p.tpl.lower == "tortoise":
        prof = [(0.0, 0.31), (0.12, 0.3), (0.22, 0.26), (0.29, 0.18), (0.31, 0.1), (0.3, 0.07), (0.0, 0.07)]
        shell = MU.lathe(f"{p.spec.id}_shell", prof, 40, screw=False)
        shell.scale = (1.0, 1.25, 1.0)
        A._place(shell, (0, 0.1, 0.0), scale=(1.0, 1.25, 1.0))
        MU.set_part_attributes(shell, p.pal.silk("mango-green"), 0.0, 0.35, K_SCALES)
        plast = MU.uv_sphere(f"{p.spec.id}_plast", 0.3, 24, 10, scale=(1.0, 1.25, 0.25))
        A._place(plast, (0, 0.1, 0.075))
        P.col(plast, p.pal.silk("khaki"), 0.45, kind=K_DETAIL)
        out += [shell, plast]
        for sx in (-1, 1):
            for sy in (-1, 1):
                fl = MU.uv_sphere(f"{p.spec.id}_flip{sx}{sy}", 0.07, 12, 8, scale=(1.6, 0.8, 0.4))
                A._place(fl, (sx * 0.3, 0.1 + sy * 0.25, 0.06), (0, 0, sx * sy * 0.5))
                out.append(P.col(fl, p.pal.skin(p.spec.skin), 0.42, kind=K_DETAIL))
    return out


# =========================================================================== garments


class Surface:
    """BVH over a set of meshes (body + garments so far) for projecting ribbons and jewellery."""

    def __init__(self, objs: list[bpy.types.Object]):
        bm = bmesh.new()
        for o in objs:
            bm.from_mesh(o.data)
        self.bvh = BVHTree.FromBMesh(bm)
        bm.free()

    def project(self, pt: V, offset: float, hint: V | None = None) -> tuple[V, V]:
        loc, nrm, _, _ = self.bvh.find_nearest(pt)
        if loc is None:
            return pt, hint or V((0, -1, 0))
        n = (pt - loc)
        n = n.normalized() if n.length > 1e-6 and (pt - loc).dot(nrm) > 0 else nrm
        return loc + n * offset, n


def ribbon(name: str, path: list[V], width: float, surf: Surface, offset: float, color, zari: int,
           thickness: float = 0.004, taper_end: float = 1.0) -> bpy.types.Object:
    """Fabric strip along a path hugging the surface; garment_uv u across, v along (zari at edges/end)."""
    pts = []
    for i in range(len(path) - 1):
        for k in range(4):
            pts.append(path[i].lerp(path[i + 1], k / 4))
    pts.append(path[-1])
    proj = [surf.project(p, offset) for p in pts]
    verts, faces, uvs = [], [], []
    n = len(proj)
    for i, (pos, nrm) in enumerate(proj):
        tan = (proj[min(i + 1, n - 1)][0] - proj[max(i - 1, 0)][0]).normalized()
        side = tan.cross(nrm).normalized()
        w = width * (1 - (1 - taper_end) * i / (n - 1))
        verts.append(pos + side * w / 2)
        verts.append(pos - side * w / 2)
        uvs += [(0.0, i / (n - 1)), (1.0, i / (n - 1))]
    for i in range(n - 1):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    MU.set_part_attributes(ob, color, 0.0, 0.38, K_GARMENT, zari=zari)
    me = ob.data
    g = me.attributes["garment_uv"]
    vals = []
    for loop in me.loops:
        vals.extend(uvs[loop.vertex_index])
    g.data.foreach_set("vector", vals)
    MU.solidify(ob, thickness, 0.0)
    MU.shade_smooth(ob, None)
    return ob


def _skirt_lathe(name: str, p: Params, sk: Skel, z_top: float, z_hem: float, r_top: float, r_hip: float,
                 r_hem: float, pleats: bool, color, zari: int) -> bpy.types.Object:
    zh = sk.z_hp
    prof = [(0.0, z_hem - 0.004), (r_hem * 0.98, z_hem - 0.004), (r_hem, z_hem + 0.004),
            (r_hem * 0.97 + r_hip * 0.03, z_hem + (zh - z_hem) * 0.25),
            (r_hip * 1.02 + (r_hem - r_hip) * 0.45, z_hem + (zh - z_hem) * 0.55),
            (r_hip, zh), (r_top, z_top - 0.01), (r_top * 0.9, z_top), (0.0, z_top)]
    bm = MU.lathe_bm(prof, 64)
    for v in bm.verts:
        v.co.y *= 0.82
        v.co.x += sk.hip_x * (v.co.z - z_hem) / max(zh - z_hem, 1e-3)
        a = math.atan2(v.co.y, v.co.x)
        if pleats and -math.pi * 0.72 < a < -math.pi * 0.28 and v.co.z < zh:
            env = math.sin((a + math.pi * 0.72) / (math.pi * 0.44) * math.pi)
            k = 1 + 0.06 * env * math.sin(a * 26) * (1 - (v.co.z - z_hem) / max(zh - z_hem, 1e-3)) ** 0.7
            v.co.x *= k
            v.co.y *= k
    ob = MU.bmesh_to_object(bm, name)
    MU.shade_smooth(ob, 60)
    MU.set_part_attributes(ob, color, 0.0, 0.38, K_GARMENT, zari=zari)
    span = z_top - z_hem
    MU.set_garment_uv(ob, lambda co: ((math.atan2(co.y, co.x) / math.tau) % 1.0, (co.z - z_hem) / span))
    return ob


def _pleat_panel(name: str, surf: "Surface", x_c: float, z_top: float, z_hem: float, w_top: float, w_hem: float,
                 color, zari: int, pleats: int = 9) -> bpy.types.Object:
    """Fan of vertical pleats hanging at the front of a skirt (the golu kosuvam / dhoti pleats)."""
    nu, nv = pleats * 4, 24
    verts, faces, uvs = [], [], []
    for j in range(nv + 1):
        v = j / nv
        z = z_hem + (z_top - z_hem) * v
        w = w_hem + (w_top - w_hem) * v ** 0.8
        for i in range(nu + 1):
            u = i / nu
            x = x_c + (u - 0.5) * w
            loc, nrm = surf.project(V((x, -0.4, z)), 0.003)
            depth = 0.007 * abs(math.sin(u * pleats * math.pi)) * (0.35 + 0.65 * (1 - v))
            verts.append(loc + nrm * depth)
            uvs.append((u, v))
    for j in range(nv):
        for i in range(nu):
            a = j * (nu + 1) + i
            faces.append((a, a + 1, a + nu + 2, a + nu + 1))
    ob = MU.new_mesh_object(name, verts, faces)
    MU.set_part_attributes(ob, color, 0.0, 0.36, K_GARMENT, zari=zari)
    g = ob.data.attributes["garment_uv"]
    vals = []
    for loop in ob.data.loops:
        vals.extend(uvs[loop.vertex_index])
    g.data.foreach_set("vector", vals)
    MU.solidify(ob, 0.0025, 0.0)
    MU.shade_smooth(ob, None)
    return ob


def _leg_drape(name: str, p: Params, sk: Skel, color, zari: int, inflate: float, limit_knee: bool = False) -> bpy.types.Object:
    """Seated garment: inflated metaball copy of pelvis + legs (saree/veshti over folded legs)."""
    b = p.build
    els = [_ell(V((sk.hip_x, 0.0, sk.z_hp + 0.035)), b.hip + inflate, (1.0, 0.8, 0.72)),
           _ell(V((sk.hip_x, -0.01, sk.z_hp + 0.09)), b.belly[0] + inflate * 0.6, (1.0, 0.85, 0.5))]
    ankles = []
    for hip, knee, ank, toe in sk.legs:
        els.append(_cap(hip, knee, b.leg_r + inflate))
        end = ank if not limit_knee else knee.lerp(ank, 0.15)
        els.append(_cap(knee, end, b.leg_r * 0.75 + inflate * 1.15))
        ankles.append(end)
    mb = MU.metaball_object(f"mb_{name}", els, 0.0055)
    ob = MU.metaball_to_mesh(mb, name)
    MU.voxel_remesh(ob, 1 / 175, smooth_iters=2)
    # cut the drape just above the ankles so the feet show
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        for a in ankles:
            if (c - a).length < b.leg_r * 0.9 and not limit_knee:
                kill.append(f)
                break
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(ob.data)
    bm.free()
    MU.set_part_attributes(ob, color, 0.0, 0.38, K_GARMENT, zari=zari)
    MU.set_garment_uv(ob, lambda co: (0.5, min(((co - a).length for a in ankles), default=1.0) / 0.22))
    MU.shade_smooth(ob, None)
    return ob


def build_attire(p: Params, sk: Skel, body: bpy.types.Object) -> list[bpy.types.Object]:
    att = p.spec.attire
    if att is None:
        return []
    out: list[bpy.types.Object] = []
    col = p.pal.silk(att.color)
    acc = p.pal.silk(att.accent)
    z_zari = 1 if att.zari == "gold" else 0
    b = p.build
    seated = p.legs in ("folded", "pendant", "lalitasana", "squat")
    lower = att.lower
    zh = sk.z_hp
    if lower in ("saree", "pavadai", "half_saree", "veshti", "panchakacham", "veshti_short"):
        if seated or p.legs == "crawl":
            out.append(_leg_drape(f"{p.spec.id}_drape", p, sk, col, z_zari, 0.011 if lower != "veshti_short" else 0.007,
                                  limit_knee=lower == "veshti_short"))
        elif p.legs != "none":
            flare = {"saree": 0.2, "pavadai": 0.21, "half_saree": 0.21, "veshti": 0.15, "panchakacham": 0.16,
                     "veshti_short": 0.14}[lower]
            hem = 0.035 if lower != "veshti_short" else zh * 0.48
            if p.legs in ("dance_one_leg", "dance_lift", "lifted_knee"):
                flare *= 1.15
                hem = max(hem, zh * 0.38)
            top = zh + (0.115 if lower in ("saree", "half_saree", "pavadai") else 0.09)
            r_top = b.belly[0] * 0.98 + 0.01
            skirt = _skirt_lathe(f"{p.spec.id}_skirt", p, sk, top, hem, r_top, b.hip + 0.022, flare,
                                 False, col, z_zari)
            out.append(skirt)
            if lower in ("saree", "panchakacham", "veshti", "half_saree", "pavadai"):
                pcol = acc if lower in ("panchakacham", "veshti") else col
                x_c = -0.035 if lower in ("saree", "half_saree") else 0.0
                out.append(_pleat_panel(f"{p.spec.id}_pleats", Surface([skirt]), x_c + sk.hip_x * 0.5, top - 0.03,
                                        hem + 0.004, 0.045, 0.1 if lower != "veshti" else 0.08, pcol, z_zari))
        else:   # fish/tortoise bodies: a short waist wrap
            wrap = _skirt_lathe(f"{p.spec.id}_wrap", p, sk, zh + 0.09, zh - 0.05, b.belly[0] + 0.012, b.hip + 0.02,
                                b.hip + 0.03, False, col, z_zari)
            out.append(wrap)
    if not out and att.upper in ("sash",):
        wrap = _skirt_lathe(f"{p.spec.id}_wrap", p, sk, zh + 0.09, zh - 0.04, b.belly[0] + 0.012, b.hip + 0.02,
                            b.hip + 0.03, False, col, z_zari)
        out.append(wrap)
    surf = Surface([body] + out)
    up = sk.up
    zs, zc = sk.z_sh, sk.z_ch
    cy = b.chest[1]
    upper = att.upper
    zr = 3 if att.zari == "gold" else 0
    if lower == "saree":           # pallu: right hip → across chest → over left shoulder → down the back
        path = [V((-b.hip * 0.9, -0.09, zh + 0.1)), V((-0.04, -cy - 0.02, zc - 0.05)), V((0.06, -cy - 0.01, zc + 0.03)),
                V((b.shoulder * 0.7, -0.02, zs + 0.04)), V((b.shoulder * 0.7, 0.06, zs - 0.02)),
                V((b.shoulder * 0.6, 0.09, zh + 0.05))]
        out.append(ribbon(f"{p.spec.id}_pallu", [up(q) for q in path], 0.085, surf, 0.006, col, 2 if zr else 0))
    if lower == "half_saree" or upper == "half_saree":
        path = [V((-b.hip * 0.8, -0.085, zh + 0.08)), V((0.0, -cy - 0.02, zc - 0.04)),
                V((b.shoulder * 0.7, -0.02, zs + 0.04)), V((b.shoulder * 0.65, 0.08, zh + 0.12))]
        out.append(ribbon(f"{p.spec.id}_davani", [up(q) for q in path], 0.07, surf, 0.006, acc, zr))
    if upper in ("angavastram", "shawl", "pallu_over_shoulders"):
        w = 0.06 if upper == "angavastram" else 0.1
        c2 = acc if upper == "angavastram" else col
        for s in (-1, 1):
            path = [V((s * 0.075, -cy - 0.04, zh + (0.06 if upper == "angavastram" else 0.12))),
                    V((s * 0.09, -cy - 0.02, zc)), V((s * b.shoulder * 0.75, -0.02, zs + 0.035)),
                    V((s * b.shoulder * 0.5, 0.05, zs + 0.01)), V((s * 0.02, 0.07, zs - 0.03))]
            out.append(ribbon(f"{p.spec.id}_anga{s}", [up(q) for q in path], w, surf, 0.006, c2, zr))
    if upper in ("sash", "deerskin", "towel_shoulder"):
        path = [V((b.shoulder * 0.7, -0.01, zs + 0.035)), V((0.02, -cy - 0.02, zc - 0.02)),
                V((-b.belly[0] * 0.9, -0.06, zh + 0.07)), V((-b.belly[0] * 0.8, 0.06, zh + 0.1)),
                V((b.shoulder * 0.6, 0.07, zs - 0.02))]
        c2 = acc
        rb = ribbon(f"{p.spec.id}_sash", [up(q) for q in path], 0.05 if upper == "sash" else 0.07, surf, 0.006, c2,
                    zr if upper == "sash" else 0)
        if upper == "deerskin":
            MU.paint_corners(rb, lambda co, n: ((0.12, 0.06, 0.03), 0.0, 0.5, K_DETAIL)
                             if math.sin(co.x * 260) * math.sin(co.z * 260 + co.y * 140) > 0.55 else None)
        out.append(rb)
    if "garland_on_shoulder" in p.spec.extras or "groom_garland" in p.spec.extras or p.jewellery == "divine":
        pass   # garlands handled with jewellery
    return out


# =========================================================================== hair, crowns, jewellery


def build_head_dress(p: Params, sk: Skel, P: A.Paint) -> list[bpy.types.Object]:
    out = []
    hc = sk.head_c
    rx, ry, rz = sk.rx, sk.ry, sk.rz
    up = sk.up
    hair_col = WHITE_HAIR if p.hair == "white_bun" else (GREY_HAIR if p.tpl.age == "elder" else HAIR)
    pid = p.spec.id

    def place(ob, loc, rot=(0, 0, 0)):
        A._place(ob, loc, rot)
        if sk.lean:
            MU.transform(ob, sk.lean_mat())
        return ob

    crown = p.crown
    if p.tpl.head_kind == "elephant":
        base_z = hc.z + rz * 0.55
    else:
        base_z = hc.z + rz * 0.5
    if crown == "kireedam":
        k = rx
        prof = [(0.0, 0.0), (k * 0.93, 0.0), (k * 0.97, 0.06 * rz), (k * 0.84, 0.16 * rz), (k * 0.9, 0.3 * rz),
                (k * 0.64, 0.5 * rz), (k * 0.7, 0.66 * rz), (k * 0.45, 0.9 * rz), (k * 0.5, 1.02 * rz),
                (k * 0.22, 1.32 * rz), (k * 0.26, 1.42 * rz), (k * 0.08, 1.62 * rz), (k * 0.13, 1.7 * rz), (0.0, 1.85 * rz)]
        kr = MU.lathe(f"{pid}_kireedam", prof, 40, screw=False)
        for v in kr.data.vertices:
            v.co.y *= ry / rx
        P.gold(kr, 0.25)
        out.append(place(kr, V((hc.x, hc.y + 0.06 * ry, base_z))))
        gem = MU.uv_sphere(f"{pid}_kgem", rz * 0.12, 10, 6, scale=(1, 0.5, 1.3))
        out.append(place(P.col(gem, P.p.silk("kumkum"), 0.15, kind=K_DETAIL), V((hc.x, hc.y - ry * 0.98, base_z + 0.1 * rz))))
    elif crown == "karanda_makuta":
        k = rx
        prof = [(0.0, 0.0), (k * 0.88, 0.0), (k * 0.92, 0.1 * rz), (k * 0.8, 0.2 * rz), (k * 0.66, 0.28 * rz),
                (k * 0.72, 0.42 * rz), (k * 0.6, 0.56 * rz), (k * 0.48, 0.64 * rz), (k * 0.54, 0.78 * rz),
                (k * 0.44, 0.9 * rz), (k * 0.34, 0.98 * rz), (k * 0.39, 1.1 * rz), (k * 0.3, 1.22 * rz),
                (k * 0.2, 1.3 * rz), (k * 0.24, 1.42 * rz), (k * 0.12, 1.55 * rz), (k * 0.16, 1.66 * rz),
                (0.0, 1.85 * rz)]
        kr = MU.lathe(f"{pid}_makuta", prof, 40, screw=False)
        for v in kr.data.vertices:
            v.co.y *= ry / rx
        P.gold(kr, 0.25)
        out.append(place(kr, V((hc.x, hc.y + 0.08 * ry, base_z))))
        gem = MU.uv_sphere(f"{pid}_mgem", rz * 0.11, 10, 6, scale=(1, 0.5, 1.3))
        out.append(place(P.col(gem, P.p.silk("kumkum"), 0.15, kind=K_DETAIL),
                         V((hc.x, hc.y - ry * 0.82, base_z + 0.12 * rz))))
    elif crown == "peacock_feather_crown":
        band = MU.torus(f"{pid}_band", rx * 0.92, rz * 0.08, 32, 6)
        band.scale = (1.0, ry / rx, 1.0)
        MU.apply_transform(band)
        out.append(place(P.gold(band), V((hc.x, hc.y + 0.05 * ry, hc.z + rz * 0.45))))
        q = A.peacock_quill(P, p.rng)
        out.append(place(q, V((hc.x + rx * 0.35, hc.y + ry * 0.1, hc.z + rz * 0.55)), (0.1, 0.35, 0)))
    elif crown == "turban_cloth":
        prof = [(0.0, 0.0), (rx * 0.98, 0.0), (rx * 1.05, 0.15 * rz), (rx * 0.98, 0.35 * rz), (rx * 0.6, 0.48 * rz),
                (0.0, 0.5 * rz)]
        tb = MU.lathe(f"{pid}_turban", prof, 32, screw=False)
        for v in tb.data.vertices:
            v.co.y *= ry / rx
            v.co.z += 0.03 * rz * math.sin(math.atan2(v.co.y, v.co.x) * 3)
        P.col(tb, P.p.silk(p.spec.attire.accent if p.spec.attire else "white"), 0.5, kind=K_GARMENT)
        out.append(place(tb, V((hc.x, hc.y + 0.04 * ry, hc.z + rz * 0.3))))
    # hair forms
    hair = p.hair
    if crown in ("none", "turban_cloth", "peacock_feather_crown") or hair in ("andal_kondai",):
        if hair in ("kondai", "loose_bun", "white_bun"):
            bun = MU.uv_sphere(f"{pid}_bun", rz * 0.5, 16, 10, scale=(1.0, 0.85, 0.85))
            out.append(place(P.col(bun, hair_col, 0.5, kind=K_HAIR), V((hc.x, hc.y + ry * 0.95, hc.z - rz * 0.15))))
        elif hair == "andal_kondai":    # tilted side knot over her left (+X), wrapped in jasmine (ICONOGRAPHY R31)
            bun = MU.uv_sphere(f"{pid}_kondai", rz * 0.62, 18, 10, scale=(1.0, 0.9, 0.85))
            out.append(place(P.col(bun, hair_col, 0.5, kind=K_HAIR), V((hc.x + rx * 0.62, hc.y + ry * 0.15, hc.z + rz * 0.78)),
                             (0, 0.6, 0)))
            orn = MU.torus(f"{pid}_kring", rz * 0.4, rz * 0.06, 24, 6)
            out.append(place(P.gold(orn), V((hc.x + rx * 0.55, hc.y + ry * 0.12, hc.z + rz * 0.7)), (0, 0.6 + math.pi / 2, 0)))
        elif hair in ("jata", "hair_knot", "kudumi", "sikha"):
            if hair == "jata":
                for i in range(3):
                    t = MU.torus(f"{pid}_jata{i}", rz * (0.42 - i * 0.1), rz * 0.13, 20, 8)
                    out.append(place(P.col(t, hair_col, 0.55, kind=K_HAIR), V((hc.x, hc.y + 0.05 * ry, hc.z + rz * (0.85 + i * 0.2)))))
                knob = MU.uv_sphere(f"{pid}_jtop", rz * 0.2, 10, 6)
                out.append(place(P.col(knob, hair_col, 0.55, kind=K_HAIR), V((hc.x, hc.y + 0.05 * ry, hc.z + rz * 1.45))))
            elif hair == "hair_knot":
                knot = MU.uv_sphere(f"{pid}_knot", rz * 0.38, 14, 8)
                out.append(place(P.col(knot, hair_col if p.tpl.age != "elder" else GREY_HAIR, 0.5, kind=K_HAIR),
                                 V((hc.x, hc.y + ry * 0.35, hc.z + rz * 0.95))))
            else:
                tuft = MU.uv_sphere(f"{pid}_tuft", rz * 0.25, 10, 6, scale=(1, 1, 1.3))
                out.append(place(P.col(tuft, HAIR, 0.5, kind=K_HAIR), V((hc.x, hc.y + ry * 0.75, hc.z + rz * 0.55))))
        elif hair == "braids":
            for s in (-1, 1):
                pts = [hc + V((s * rx * 0.7, ry * 0.6, -rz * 0.3)), hc + V((s * rx * 0.9, ry * 0.7, -rz * 1.4)),
                       hc + V((s * rx * 0.85, ry * 0.85, -rz * 2.6))]
                br = MU.tube(f"{pid}_braid{s}", pts, rz * 0.16, radii=[1, 0.9, 0.6])
                out.append(place(P.col(br, HAIR, 0.5, kind=K_HAIR), V((0, 0, 0))))
                rib = MU.uv_sphere(f"{pid}_ribbon{s}", rz * 0.14, 8, 6)
                out.append(place(P.col(rib, P.p.silk("kumkum"), 0.4, kind=K_DETAIL), pts[-1] + V((0, 0, -rz * 0.1))))
    # jasmine (goddesses, brides and women with jasmine in extras)
    wants_jasmine = "jasmine" in p.spec.extras or (p.tpl.jewellery == "divine" and p.build.bust > 0)
    if wants_jasmine:
        if hair == "andal_kondai":
            centre = V((hc.x + rx * 0.62, hc.y + ry * 0.15, hc.z + rz * 0.78))
            radius, tilt = rz * 0.62, (0, 0.6, 0)
        elif crown in ("karanda_makuta", "kireedam"):
            centre = V((hc.x, hc.y + ry * 0.75, hc.z - rz * 0.05))
            radius, tilt = rz * 0.55, (math.pi / 2, 0, 0)
        else:
            centre = V((hc.x, hc.y + ry * 0.95, hc.z - rz * 0.15))
            radius, tilt = rz * 0.5, (math.pi / 2 - 0.2, 0, 0)
        buds = []
        n = 22
        for i in range(n):
            a = i / n * math.tau
            bud = A.leaf_shell(f"{pid}_jas{i}", rz * 0.2, rz * 0.08, cup=0.6)
            bud.rotation_euler = (math.pi / 2, 0, a)
            MU.apply_transform(bud)
            A._place(bud, (math.cos(a) * radius, math.sin(a) * radius, 0))
            buds.append(bud)
        ring = MU.join(buds, f"{pid}_jasmine")
        P.col(ring, P.p.material("jasmine"), 0.5, kind=K_DETAIL)
        A._place(ring, V((0, 0, 0)), tilt)
        out.append(place(ring, centre))
    if "wild_flowers_hair" in p.spec.extras or "flowers_hair" in p.spec.extras:
        for i in range(5):
            f = MU.uv_sphere(f"{pid}_flower{i}", rz * 0.1, 8, 6)
            col = P.p.silk("kumkum") if i % 2 else P.p.material("marigold-orange")
            out.append(place(P.col(f, col, 0.5, kind=K_DETAIL),
                             V((hc.x + (i - 2) * rx * 0.25, hc.y + ry * 0.9, hc.z + rz * 0.1))))
    return out


def build_jewellery(p: Params, sk: Skel, P: A.Paint, surf: Surface) -> list[bpy.types.Object]:
    level = p.jewellery
    ex = set(p.spec.extras)
    out = []
    b = p.build
    hc = sk.head_c
    pid = p.spec.id
    up = sk.up

    def chain(name, pts_up, bead_r, color=None, gold=True, every=0.012):
        objs = []
        path = [up(q) for q in pts_up]
        dense = []
        for i in range(len(path) - 1):
            seg = (path[i + 1] - path[i]).length
            k = max(1, int(seg / every))
            for j in range(k):
                dense.append(path[i].lerp(path[i + 1], j / k))
        dense.append(path[-1])
        for i, q in enumerate(dense):
            loc, nrm = surf.project(q, bead_r * 1.1)
            bead = MU.uv_sphere(f"{name}{i}", bead_r, 8, 6)
            A._place(bead, loc)
            objs.append(P.gold(bead) if gold else P.col(bead, color, 0.35, kind=K_DETAIL))
        if not objs:
            return None
        return MU.join(objs, name)

    zs, zc = sk.z_sh, sk.z_ch
    cy = b.chest[1]

    def necklace(i, drop, bead):
        pts = [V((-0.05, -0.02, zs + 0.04)), V((-0.045, -cy * 0.8, zc + 0.03 - drop * 0.5)),
               V((0.0, -cy - 0.01, zc - drop)), V((0.045, -cy * 0.8, zc + 0.03 - drop * 0.5)), V((0.05, -0.02, zs + 0.04))]
        return chain(f"{pid}_neck{i}", pts, bead)

    if level in ("simple", "royal", "divine") or "gold_chain" in ex:
        out.append(necklace(0, 0.0, 0.0042))
    if level in ("royal", "divine"):
        out.append(necklace(1, 0.06, 0.0048))
        pend = MU.uv_sphere(f"{pid}_pend", 0.013, 12, 8, scale=(1, 0.5, 1.3))
        loc, _ = surf.project(up(V((0, -cy - 0.02, zc - 0.07))), 0.012)
        A._place(pend, loc)
        out.append(P.col(pend, P.p.silk("kumkum"), 0.15, kind=K_DETAIL))
    if level == "divine":
        out.append(necklace(2, 0.12, 0.0045))
    if "bead_necklace" in ex or "rudraksha" in ex or "tulasi_mala" in ex:
        colr = (0.25, 0.08, 0.04) if "rudraksha" in ex else ((0.9, 0.85, 0.7) if "tulasi_mala" in ex else P.p.silk("kumkum"))
        pts = [V((-0.05, -0.02, zs + 0.035)), V((0.0, -cy - 0.02, zc - 0.03)), V((0.05, -0.02, zs + 0.035))]
        out.append(chain(f"{pid}_mala", pts, 0.006, colr, gold=False))
    if level == "divine" or "sacred_thread" in ex or "sacred_thread_serpent" in ex:
        path = [V((b.shoulder * 0.55, -0.01, zs + 0.03)), V((0.0, -cy - 0.01, zc - 0.03)),
                V((-b.belly[0] * 0.9, -0.05, sk.z_hp + 0.08))]
        col = P.p.silk("white") if "sacred_thread_serpent" not in ex else P.p.silk("mango-green")
        th = chain(f"{pid}_thread", path, 0.0035 if "sacred_thread_serpent" not in ex else 0.007, col, gold=False,
                   every=0.006)
        out.append(th)
    if level in ("royal", "divine", "simple") and p.tpl.head_kind in ("human", "elephant"):
        for s in (-1, 1):   # earrings
            e = MU.torus(f"{pid}_ear{s}", sk.rz * 0.13, sk.rz * 0.04, 16, 5)
            ear_pt = hc + V((s * sk.rx * 1.0, 0.02, -sk.rz * 0.35))
            if p.tpl.head_kind == "elephant":
                continue
            A._place(e, up(ear_pt), (0, math.pi / 2, 0))
            drop = MU.uv_sphere(f"{pid}_eard{s}", sk.rz * 0.07, 8, 6)
            A._place(drop, up(ear_pt - V((0, 0, sk.rz * 0.18))))
            out += [P.gold(e), P.gold(drop)]
    if "nose_ring" in ex:
        nr = MU.torus(f"{pid}_nose", sk.rz * 0.08, sk.rz * 0.018, 14, 4)
        A._place(nr, up(hc + V((sk.rx * 0.12, -sk.ry * 1.0, -sk.rz * 0.2))), (0, math.pi / 2, 0))
        out.append(P.gold(nr))
    # armlets & bangles
    if level in ("royal", "divine", "simple"):
        for arm in sk.arms:
            r = b.arm_r * (1.0 if arm.pair == 0 else 0.9)
            d = (arm.elbow - arm.shoulder).normalized()
            if level != "simple":
                kl = MU.torus(f"{pid}_keyura{arm.side}{arm.pair}", r * 1.15, r * 0.28, 16, 5)
                rot = V((0, 0, 1)).rotation_difference(d).to_euler()
                A._place(kl, arm.shoulder.lerp(arm.elbow, 0.45), rot)
                out.append(P.gold(kl))
            dw = (arm.wrist - arm.elbow).normalized()
            for k in range(2):
                bg = MU.torus(f"{pid}_bangle{arm.side}{arm.pair}{k}", r * 0.92, r * 0.18, 16, 5)
                A._place(bg, arm.elbow.lerp(arm.wrist, 0.86 - k * 0.1), V((0, 0, 1)).rotation_difference(dw).to_euler())
                out.append(P.gold(bg))
    # waist belt (oddiyanam) for goddesses and brides
    if level in ("divine", "royal") and p.legs not in ("crawl",):
        zw = sk.z_hp + 0.1
        pts = []
        for i in range(24):
            a = i / 24 * math.tau
            pts.append(V((math.cos(a) * 0.2, math.sin(a) * 0.2, zw)))
        beads = []
        for i, q in enumerate(pts):
            loc, nrm = surf.project(up(q), 0.008)
            bd = MU.uv_sphere(f"{pid}_belt{i}", 0.009, 8, 6, scale=(1, 1, 1.4))
            A._place(bd, loc)
            beads.append(bd)
        belt = MU.join(beads, f"{pid}_belt")
        out.append(P.gold(belt))
        loc, _ = surf.project(up(V((0, -0.2, zw))), 0.012)
        med = MU.uv_sphere(f"{pid}_beltmed", 0.02, 12, 8, scale=(1.3, 0.5, 1))
        A._place(med, loc)
        out.append(P.gold(med))
    # anklets
    if "anklets" in ex or level == "divine":
        for leg in sk.legs:
            a = MU.torus(f"{pid}_anklet{leg[0].x:.2f}", b.leg_r * 0.85, b.leg_r * 0.2, 16, 5)
            d = (leg[2] - leg[1]).normalized()
            A._place(a, leg[1].lerp(leg[2], 0.85), V((0, 0, 1)).rotation_difference(d).to_euler())
            out.append(P.gold(a))
    if "waist_chain" in ex:
        zw = sk.z_hp + 0.03
        beads = []
        for i in range(20):
            a = i / 20 * math.tau
            loc, _ = surf.project(up(V((math.cos(a) * 0.2, math.sin(a) * 0.2, zw))), 0.006)
            bd = MU.uv_sphere(f"{pid}_wchain{i}", 0.006, 8, 6)
            A._place(bd, loc)
            beads.append(bd)
        out.append(P.gold(MU.join(beads, f"{pid}_wchain")))
    # garlands worn (vanamala for divine figures, groom's garland, Andal's garland)
    if level == "divine" or "groom_garland" in ex or "garland_on_shoulder" in ex:
        drop = 0.3 if level == "divine" and p.legs not in ("folded", "lalitasana", "pendant") else 0.18
        pts = [V((-0.06, -0.01, zs + 0.03)), V((-0.08, -cy - 0.02, zc - drop * 0.5)), V((0.0, -cy - 0.05, zc - drop)),
               V((0.08, -cy - 0.02, zc - drop * 0.5)), V((0.06, -0.01, zs + 0.03))]
        g = chain(f"{pid}_vanamala", pts, 0.0075, P.p.material("marigold-orange"), gold=False, every=0.011)
        if g is not None:
            MU.paint_corners(g, lambda co, n: (P.p.silk("kumkum"), 0.0, 0.5, K_DETAIL)
                             if int(abs(co.x) * 120 + co.z * 90) % 3 == 0 else
                             ((P.p.material("jasmine"), 0.0, 0.5, K_DETAIL) if int(co.z * 140) % 4 == 0 else None))
            out.append(g)
    return [o for o in out if o is not None]


# =========================================================================== hands & attributes


def build_hands_and_items(p: Params, sk: Skel, P: A.Paint) -> list[bpy.types.Object]:
    out = []
    done_two = set()
    for name, frame in sk.items:
        if name in done_two:
            continue
        done_two.add(name)
        it = A.build_attribute(name, p.pal, p.rng)
        MU.transform(it, sk.lean_mat() @ frame)
        out.append(it)
    for arm in sk.arms:
        tok = arm.token
        if tok in TWO_HANDED and arm.pair == 0 and sk.items:
            continue
        if A.is_mudra(tok):
            if tok in ("abhaya_coins", "varada_coins"):
                out.append(_coin_stream(p, arm, P))
            continue
        it = A.build_attribute(tok, p.pal, p.rng)
        grip = arm.wrist + arm.hand_dir * 0.03 + arm.palm * (-0.004)
        up_ax = arm.grip_up
        rot = V((0, 0, 1)).rotation_difference(up_ax)
        MU.transform(it, Matrix.Translation(grip) @ rot.to_matrix().to_4x4())
        out.append(it)
    return out


def _coin_stream(p: Params, arm: Arm, P: A.Paint) -> bpy.types.Object:
    coins = []
    start = arm.wrist + arm.hand_dir * 0.04
    for i in range(9):
        c = MU.cylinder(f"{p.spec.id}_coin{arm.side}{i}", 0.011, 0.0025, 14)
        pos = start + V((arm.side * 0.006 * math.sin(i), -0.012, -0.022 * i))
        A._place(c, pos, (p.rng.uniform(0, 3), p.rng.uniform(0, 3), 0))
        coins.append(P.gold(c, 0.22))
    return MU.join(coins, f"{p.spec.id}_coins{arm.side}")


# =========================================================================== extras


def build_extras(p: Params, sk: Skel, P: A.Paint, surf: Surface) -> list[bpy.types.Object]:
    ex = set(p.spec.extras)
    out = []
    b = p.build
    pid = p.spec.id
    up = sk.up
    hc = sk.head_c
    zh, zc, zs = sk.z_hp, sk.z_ch, sk.z_sh
    if "id_badge" in ex:
        out.append(_ribbon_simple(p, sk, surf, "badge", P.p.silk("nilambara"), [V((-0.045, -0.02, zs + 0.03)),
                                  V((0.0, -b.chest[1] - 0.01, zc - 0.06)), V((0.045, -0.02, zs + 0.03))], 0.012))
        card = MU.box(f"{pid}_card", (0.03, 0.004, 0.04), (0, 0, 0), bevel=0.002)
        loc, _ = surf.project(up(V((0, -b.chest[1] - 0.02, zc - 0.075))), 0.006)
        A._place(card, loc)
        out.append(P.col(card, P.p.silk("white"), 0.4, kind=K_DETAIL))
    if "spectacles" in ex:
        for s in (-1, 1):
            r = MU.torus(f"{pid}_spec{s}", sk.rz * 0.2, sk.rz * 0.03, 16, 4)
            A._place(r, up(hc + V((s * sk.rx * 0.38, -sk.ry * 0.98, sk.rz * 0.02))), (math.pi / 2, 0, 0))
            out.append(P.col(r, (0.03, 0.03, 0.03), 0.3, kind=K_DETAIL))
    if "quiver" in ex:
        q = MU.cylinder(f"{pid}_quiver", 0.025, 0.2, 12, radius_top=0.03)
        A._place(q, up(V((0.06, 0.1, zc - 0.02))), (0.0, -0.4, 0))
        out.append(P.col(q, P.p.silk("maroon"), 0.4, kind=K_DETAIL))
        for i in range(3):
            ar = MU.cylinder(f"{pid}_qa{i}", 0.003, 0.08, 6)
            A._place(ar, up(V((0.06 + 0.035 + i * 0.008, 0.1, zc + 0.1))), (0.0, -0.4, 0))
            out.append(P.col(ar, P.p.silk("khaki"), 0.5, kind=K_DETAIL))
    if "bow_on_shoulder" in ex:
        bw = A.bow(P, p.rng, 0.4)
        A._place(bw, up(V((0.1, 0.07, zc - 0.05))), (0.0, 0.35, 0))
        out.append(bw)
    if "hiranyakashipu_on_lap" in ex:
        lz = zh + b.leg_r + 0.03
        hy = -0.16
        els = [_ell(V((-0.02, hy, lz)), 0.052, (2.0, 0.85, 0.8)),                     # torso across the lap
               _cap(V((-0.13, hy, lz + 0.01)), V((-0.18, hy - 0.01, lz + 0.03)), 0.026),  # neck
               _ball(V((-0.225, hy - 0.015, lz + 0.05)), 0.055),                          # head, thrown back
               _cap(V((0.08, hy, lz - 0.005)), V((0.17, hy - 0.01, lz - 0.03)), 0.034),   # hips/thighs
               _cap(V((0.17, hy - 0.01, lz - 0.03)), V((0.2, hy - 0.02, lz - 0.16)), 0.025),  # legs hanging
               _cap(V((-0.1, hy - 0.02, lz)), V((-0.12, hy - 0.05, lz - 0.12)), 0.018)]      # arm hanging
        mb = MU.metaball_object(f"mb_{pid}_hk", els, 0.005)
        hk = MU.metaball_to_mesh(mb, f"{pid}_hiranya")
        MU.voxel_remesh(hk, 1 / 175, 2)
        P.col(hk, P.p.skin("wheat"), 0.42, kind=K_DETAIL)
        head_c = V((-0.225, hy - 0.015, lz + 0.05))

        def hk_paint(co, n):
            if 0.04 < co.x < 0.24 and co.z > lz - 0.1:
                return (P.p.silk("parrot-green"), 0.0, 0.4, K_DETAIL)
            if (co - head_c).length < 0.075 and (co.x < head_c.x - 0.02 or co.y > head_c.y + 0.02):
                return ((0.02, 0.015, 0.012), 0.0, 0.35, K_HAIR)
            return None
        MU.paint_corners(hk, hk_paint)
        crown = MU.cylinder(f"{pid}_hkcrown", 0.034, 0.055, 12, radius_top=0.012)
        A._place(crown, head_c + V((-0.035, 0.0, 0.035)), (0, -0.9, 0))
        out += [hk, P.gold(crown)]
        for e in (-1, 1):
            eye = MU.uv_sphere(f"{pid}_hkeye{e}", 0.007, 8, 6)
            A._place(eye, head_c + V((0.012 + e * 0.012, -0.05, 0.01)))
            out.append(P.col(eye, (0.01, 0.01, 0.01), 0.2, kind=K_DETAIL))
    if "coin_pile" in ex:
        coins = []
        for i in range(18):
            c = MU.cylinder(f"{pid}_pile{i}", 0.011, 0.0025, 12)
            a = i * 2.4
            r = 0.012 * math.sqrt(i)
            A._place(c, V((0.16 + math.cos(a) * r, -0.2 + math.sin(a) * r, 0.003 + (i % 5) * 0.003)),
                     (p.rng.uniform(-0.3, 0.3), p.rng.uniform(-0.3, 0.3), 0))
            coins.append(P.gold(c, 0.22))
        out.append(MU.join(coins, f"{pid}_pile"))
    if "vegetable_basket" in ex:
        out.append(_veg_basket(p, P, V((0.0, -0.2, 0.0))))
    if "churning_pot" in ex:
        pot = MU.lathe(f"{pid}_cpot", [(0.0, 0.0), (0.05, 0.0), (0.085, 0.06), (0.08, 0.12), (0.06, 0.15),
                                       (0.065, 0.16), (0.0, 0.15)], 28, screw=False)
        A._place(pot, V((0, -0.2, 0.0)))
        out.append(P.mat(pot, "terracotta", 0.6))
    if "pot_on_head" in ex:
        pot = A.butter_pot(P, p.rng, 2.2)
        A._place(pot, up(hc + V((0, 0, sk.rz * 1.0))))
        out.append(pot)
    if "thavil_drum_on_strap" in ex:
        drum = MU.lathe(f"{pid}_thavil", [(0.0, -0.09), (0.07, -0.09), (0.085, -0.04), (0.088, 0.0), (0.085, 0.04),
                                          (0.07, 0.09), (0.0, 0.09)], 28, screw=False)
        A._place(drum, up(V((0.0, -0.17, zh + 0.04))), (0, math.pi / 2, 0))
        P.col(drum, P.p.silk("maroon"), 0.35, kind=K_DETAIL)
        MU.paint_corners(drum, lambda co, n: (P.p.silk("sandal"), 0.0, 0.6, K_DETAIL) if abs(n.x) > 0.8 else None)
        out.append(drum)
    if "uzhavarappadai_on_shoulder" in ex:
        shaft = MU.cylinder(f"{pid}_uzh", 0.006, 0.42, 8)
        A._place(shaft, up(V((0.07, -0.08, zc + 0.02))), (0.25, 0.2, 0))
        blade = MU.box(f"{pid}_uzhb", (0.04, 0.006, 0.03), (0, 0, 0), bevel=0.002)
        A._place(blade, up(V((0.07 + 0.042, -0.08 + 0.05, zc + 0.02 + 0.2))), (0.25, 0.2, 0))
        out += [P.col(shaft, P.p.silk("khaki"), 0.5, kind=K_DETAIL), P.silver(blade)]
    if "golden_cymbals_at_feet" in ex:
        for s in (-1, 1):
            c = MU.lathe(f"{pid}_cym{s}", [(0.0, 0.0), (0.025, 0.002), (0.028, 0.006), (0.0, 0.01)], 20, screw=False)
            A._place(c, V((s * 0.09, -0.14, 0.0)), (0.3 * s, 0, 0))
            out.append(P.gold(c))
    if "mini_kolam" in ex:
        out.append(_mini_kolam(p, V((0.0, -0.32, 0.0))))
    if "infant_on_lap" in ex and "infant" not in p.spec.attributes:
        inf = A.infant(P, p.rng)
        A._place(inf, V((0.0, -0.14, sk.z_hp + 0.02)))
        out.append(inf)
    return out


def _ribbon_simple(p, sk, surf, tag, color, pts, width):
    return ribbon(f"{p.spec.id}_{tag}", [sk.up(q) for q in pts], width, surf, 0.005, color, 0, 0.003)


def _veg_basket(p: Params, P: A.Paint, at: V) -> bpy.types.Object:
    bk = MU.lathe(f"{p.spec.id}_basket", [(0.0, 0.0), (0.06, 0.0), (0.1, 0.05), (0.11, 0.06), (0.0, 0.03)], 28,
                  screw=False)
    P.col(bk, P.p.silk("khaki"), 0.6, kind=K_DETAIL)
    MU.paint_corners(bk, lambda co, n: ((0.3, 0.2, 0.08), 0.0, 0.6, K_DETAIL)
                     if math.sin(math.atan2(co.y, co.x) * 24) * math.sin(co.z * 300) > 0.2 else None)
    parts = [bk]
    rng = p.rng
    veg = [("brinjal", (1, 1, 1.6), 0.016), ("kumkum", (1, 1, 1), 0.015), ("parrot-green", (1, 1, 4), 0.007),
           ("mango-green", (1, 1, 8), 0.005)]
    for i in range(16):
        key, sc, r = veg[i % 4]
        a = rng.uniform(0, math.tau)
        d = rng.uniform(0, 0.07)
        v = MU.uv_sphere(f"{p.spec.id}_veg{i}", r, 10, 6, scale=sc)
        A._place(v, (math.cos(a) * d, math.sin(a) * d, 0.05 + rng.uniform(0, 0.015)),
                 (rng.uniform(0, 1.5), rng.uniform(0, 1.5), 0))
        parts.append(P.col(v, P.p.silk(key), 0.35, kind=K_DETAIL))
    ob = MU.join(parts, f"{p.spec.id}_basket")
    A._place(ob, at)
    return ob


def _mini_kolam(p: Params, at: V) -> bpy.types.Object:
    from . import props as PR
    k = PR.build_kolam(f"{p.spec.id}_minikolam", 5, 0.035, p.rng, None, line_width=0.004, density=0.3)
    MU.set_part_attributes(k, p.pal.material("rice-flour"), 0.0, 0.9, K_DETAIL)
    k.data.materials.clear()
    A._place(k, at)
    return k


# =========================================================================== pedestal & vahana


def build_pedestal(p: Params, sk: Skel, P: A.Paint, footprint: float) -> list[bpy.types.Object]:
    seat = p.spec.seat
    out = []
    pid = p.spec.id
    rad = max(footprint * 0.62, 0.17)
    ped_col = P.p.material("pedestal")
    if seat in ("pedestal", "plinth", "water_pedestal", "pillar_throne", "cloud_pedestal") or (
            seat in SEAT_RAISED and p.legs not in ("pendant", "lalitasana")):
        h = 0.05
        prof = [(0.0, -h), (rad * 1.06, -h), (rad * 1.08, -h + 0.012), (rad * 1.0, -h + 0.018), (rad * 0.97, -0.006),
                (rad * 0.99, 0.0), (0.0, 0.0)]
        ped = MU.lathe(f"{pid}_ped", prof, 48, screw=False)
        for v in ped.data.vertices:
            v.co.y *= 0.78
        col = P.p.silk("peacock-blue") if seat == "water_pedestal" else ped_col
        P.col(ped, col, 0.35, kind=K_DETAIL)
        MU.paint_corners(ped, lambda co, n: (P.p.material("gold"), 1.0, 0.28, K_GOLD) if abs(co.z + h + 0.014) < 0.004 else
                         ((P.p.silk("white"), 0.0, 0.35, K_DETAIL) if seat == "water_pedestal" and
                          math.sin(math.atan2(co.y, co.x) * 14 + co.z * 120) > 0.85 else None))
        out.append(ped)
        if seat == "cloud_pedestal":
            els = [_ball(V((math.cos(a) * rad * 0.7, math.sin(a) * rad * 0.55, 0.0)), 0.05)
                   for a in (i / 7 * math.tau for i in range(7))]
            mb = MU.metaball_object(f"mb_{pid}_cloud", els, 0.008)
            cl = MU.metaball_to_mesh(mb, f"{pid}_cloud")
            out.append(P.col(cl, P.p.silk("white"), 0.4, kind=K_DETAIL))
        if seat == "pillar_throne":
            pil = MU.lathe(f"{pid}_pillar", [(0.0, 0.0), (0.06, 0.0), (0.05, 0.03), (0.045, 0.45), (0.06, 0.47),
                                             (0.0, 0.47)], 16, screw=False)
            A._place(pil, V((0.0, 0.16, 0.0)))
            out.append(P.col(pil, P.p.material("granite"), 0.5, kind=K_DETAIL))
            stool = MU.box(f"{pid}_stool", (0.3, 0.22, sk.z_hp - 0.06), (0, 0.02, (sk.z_hp - 0.06) / 2), bevel=0.01)
            out.append(P.col(stool, P.p.silk("maroon"), 0.35, kind=K_DETAIL))
    if seat in ("lotus_seat", "white_lotus_seat"):
        white = seat == "white_lotus_seat"
        top = (p.seat_h if p.legs in ("pendant", "lalitasana") else 0.0) + 0.02
        top = max(top, 0.06)
        core = MU.cylinder(f"{pid}_lcore", rad * 0.75, top, 32, center=(0, 0, top / 2 - 0.02))
        P.col(core, P.p.silk("mango-green"), 0.4, kind=K_DETAIL)
        out.append(core)
        for ring, (n, ln, tilt, z) in enumerate(((14, rad * 0.75, 1.1, top - 0.03), (12, rad * 0.62, 0.75, top - 0.005))):
            for i in range(n):
                a = (i + 0.5 * ring) / n * math.tau
                pet = A.leaf_shell(f"{pid}_lp{ring}_{i}", ln, ln * 0.6, cup=0.45)
                A.gradient_paint(pet, P.p.silk("white"), P.p.silk("white") if white else P.p.silk("lotus-pink"),
                                 rough=0.35, kind=K_DETAIL)
                pet.rotation_euler = (tilt, 0, 0)
                MU.apply_transform(pet)
                pet.rotation_euler = (0, 0, a + math.pi / 2)
                MU.apply_transform(pet)
                A._place(pet, (math.cos(a) * rad * 0.55, math.sin(a) * rad * 0.55, z))
                out.append(pet)
        if p.legs in ("pendant", "lalitasana"):
            foot = MU.cylinder(f"{pid}_footrest", 0.05, 0.02, 20, center=(0, 0, 0.0))
            ankle = [leg[2] for leg in sk.legs if leg[2].z < 0.15]
            if ankle:
                A._place(foot, V((ankle[0].x, ankle[0].y - 0.02, -0.01)))
                out.append(P.col(foot, P.p.silk("lotus-pink"), 0.4, kind=K_DETAIL))
    if seat == "peetam":
        h = max(p.seat_h - 0.0, 0.12) if p.legs in ("pendant", "lalitasana") else 0.09
        tiers = [(rad * 1.25, 0.0, h * 0.25), (rad * 1.1, h * 0.25, h * 0.75), (rad * 1.2, h * 0.75, h)]
        for i, (w, z0, z1) in enumerate(tiers):
            t = MU.box(f"{pid}_peetam{i}", (w * 2, w * 1.5, z1 - z0), (0, 0.02, (z0 + z1) / 2 - 0.01), bevel=0.006)
            P.col(t, P.p.silk("maroon") if i != 1 else P.p.material("pedestal"), 0.35, kind=K_DETAIL)
            if i == 1:
                MU.paint_corners(t, lambda co, n: (P.p.material("gold"), 1.0, 0.28, K_GOLD)
                                 if math.sin(co.x * 160) > 0.7 and n.y < -0.5 else None)
            out.append(t)
    return out


def attach_vahana(p: Params, sk: Skel) -> tuple[list[bpy.types.Object], float]:
    """Rider's mount (or Gaja Lakshmi's elephants) in rider units. Returns parts and the vertical lift applied
    to the rider so the pelvis sits on the saddle."""
    kind = p.spec.vahana
    if not kind or kind in ("kaliya",):
        return [], 0.0
    ob, saddle = VH.build_vahana(kind, p.pal, p.rng, "standing")
    s = VH.size_m(kind) / p.H
    if kind == "gaja_pair":
        A._place(ob, V((0, 0.12, 0.0)), scale=(s, s, s))
        return [ob], 0.0
    if p.spec.pose == "riding" and saddle is not None:
        heading = -1 if p.spec.position.x > 0 else 1        # mount faces the centre of the step
        A._place(ob, V((0, 0.0, 0.0)), (0, 0, 0 if heading > 0 else math.pi), (s, s, s))
        lift = saddle.translation.z * s - (sk.z_hp - 0.02)
        return [ob], lift
    # standing companion vahana (mouse at Ganesha's feet, swan beside Saraswati)
    if kind == "mouse":
        A._place(ob, V((0.12, -0.24, 0.0)), (0, 0, 0.4), (s, s, s))
    elif kind == "swan":
        A._place(ob, V((0.28, -0.08, 0.0)), (0, 0, math.pi * 0.85), (s, s, s))
    else:
        A._place(ob, V((0.3, 0.05, 0.0)), (0, 0, math.pi), (s, s, s))
    return [ob], 0.0


# =========================================================================== assembly


def write_face_props(ob: bpy.types.Object, p: Params, sk: Skel) -> None:
    hk = p.tpl.head_kind
    hc = sk.up(sk.head_c)
    ob["head_center"] = (hc.x, hc.y, hc.z)
    ob["head_radius"] = sk.rz
    ob["face_yaw"] = 0.0
    child = p.tpl.age in ("child", "infant")
    face = dict(eye_x=0.36, eye_z=0.02, eye_w=0.17, eye_h=0.072, iris_scale=0.95, has_brow=1.0, has_lips=1.0,
                mark_z=0.4, moustache=1.0 if "moustache" in p.spec.extras else 0.0)
    if child:
        face.update(eye_w=0.19, eye_h=0.085, eye_z=0.0, mark_z=0.36)
    if hk == "elephant":
        face.update(eye_x=0.44, eye_z=0.1, eye_w=0.1, eye_h=0.048, has_brow=0.0, has_lips=0.0, mark_z=0.62)
    elif hk == "lion":
        face.update(eye_x=0.33, eye_z=0.2, eye_w=0.12, eye_h=0.07, has_lips=0.0, mark_z=0.62, iris_scale=0.85)
    elif hk == "boar":
        face.update(eye_x=0.38, eye_z=0.22, eye_w=0.1, eye_h=0.05, has_lips=0.0, mark_z=0.62)
    elif hk == "marapachi":
        face.update(eye_w=0.15, eye_h=0.06, iris_scale=1.1)
    for k, v in face.items():
        ob[k] = float(v)
    ob["mark_type"] = float(MARK_IDS.get(p.mark, 0))
    pack_face_props(ob)


def pack_face_props(ob: bpy.types.Object) -> None:
    """Pack face parameters into 5 vector props (EEVEE: max 8 uniform attributes per material)."""
    g = lambda k, d=0.0: float(ob.get(k, d))
    hc = ob.get("head_center", (0.0, 0.0, -10.0))
    ob["face_a"] = (float(hc[0]), float(hc[1]), float(hc[2]))
    ob["face_b"] = (g("head_radius", 1.0), g("face_yaw"), g("mark_type"))
    ob["face_c"] = (g("eye_x"), g("eye_z"), g("eye_w", 0.01))
    ob["face_d"] = (g("eye_h", 0.01), g("iris_scale", 1.0), g("mark_z"))
    ob["face_e"] = (g("has_brow"), g("has_lips"), g("moustache"))


def build_figure(p: Params, collection) -> bpy.types.Object:
    sk = build_skeleton(p)
    sk.arms = _arms(p, sk)
    P = A.Paint(p.pal)
    body = build_body(p, sk)
    parts = [body]
    parts += special_head_parts(p, sk, P)
    parts += lower_body_parts(p, sk, P)
    garments = build_attire(p, sk, body)
    parts += garments
    surf = Surface([body] + garments)
    parts += build_head_dress(p, sk, P)
    parts += build_jewellery(p, sk, P, surf)
    parts += build_hands_and_items(p, sk, P)
    parts += build_extras(p, sk, P, surf)
    vparts, lift = attach_vahana(p, sk)
    if lift:
        for o in parts:
            MU.transform(o, Matrix.Translation(V((0, 0, lift))))
    parts += vparts
    footprint = max((max(abs(v.co.x) for v in o.data.vertices) for o in parts if o.data.vertices), default=0.2)
    footprint = min(footprint, 0.4)
    if not (p.spec.pose == "riding"):
        parts += build_pedestal(p, sk, P, footprint)
    else:
        parts += _plinth_under(p, P, vparts)
    return finalize(parts, p, sk, collection)


def _plinth_under(p: Params, P: A.Paint, vparts) -> list[bpy.types.Object]:
    if not vparts:
        return []
    lo, hi = MU.bounds_local(vparts[0])
    w, d = (hi.x - lo.x) * 0.6, (hi.y - lo.y) * 0.75
    ped = MU.box(f"{p.spec.id}_plinth", (w * 2.1 / 1.0, max(d * 1.6, 0.25), 0.05), ((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, -0.025),
                 bevel=0.01)
    P.col(ped, P.p.material("pedestal"), 0.35, kind=K_DETAIL)
    MU.paint_corners(ped, lambda co, n: (P.p.material("gold"), 1.0, 0.28, K_GOLD) if abs(co.z + 0.012) < 0.004 else None)
    return [ped]


def finalize(parts: list[bpy.types.Object], p: Params, sk: Skel, collection) -> bpy.types.Object:
    for o in parts:
        if not o.users_collection:
            bpy.context.scene.collection.objects.link(o)
        MU.apply_transform(o)
        if o.data.attributes.get("paint") is None:
            MU.set_part_attributes(o, p.pal.material("gold"), 1.0, 0.3, K_GOLD)
    ob = MU.join(parts, p.spec.id)
    MU.set_origin_bottom_center(ob)
    shift = ob.location.copy()
    ob.location = (0, 0, 0)
    write_face_props(ob, p, sk)
    hc = V(ob["head_center"]) - shift
    ob["head_center"] = (hc.x, hc.y, hc.z)
    ob["hotspot_local"] = (hc.x, hc.y, hc.z + sk.rz * 0.3)
    pack_face_props(ob)
    MU.shade_smooth(ob, None)
    sub = MU.add_subsurf(ob, 1, 1)
    M_ = M.clay_gloss()
    ob.data.materials.clear()
    ob.data.materials.append(M_)
    ob.scale = (p.H, p.H, p.H)
    ob["doll_id"] = p.spec.id
    ob["step"] = p.spec.step
    ob["slot"] = p.spec.position.slot
    ob["archetype"] = p.spec.archetype
    ob["unit_height"] = p.H
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def build_animal(spec: DollSpec, cfg: GoluConfig, collection) -> bpy.types.Object:
    rng = rng_for("doll", spec.id)
    P = A.Paint(cfg.palette)
    ob, _ = VH.build_vahana(spec.vahana, cfg.palette, rng, spec.pose)
    size = VH.size_m(spec.vahana) * spec.scale
    parts = [ob]
    if spec.seat != "none":
        lo, hi = MU.bounds_local(ob)
        low = [v.co for v in ob.data.vertices if v.co.z < lo.z + (hi.z - lo.z) * 0.3]
        lo = V((min(c.x for c in low), min(c.y for c in low), lo.z))
        hi = V((max(c.x for c in low), max(c.y for c in low), hi.z))
        w, d = hi.x - lo.x, hi.y - lo.y
        prof = [(0.0, -0.08), (0.53, -0.08), (0.54, -0.06), (0.5, -0.05), (0.5, 0.0), (0.0, 0.0)]
        ped = MU.lathe(f"{spec.id}_ped", prof, 40, screw=False)
        for v in ped.data.vertices:
            v.co.x *= max(w, 0.6) * 1.05
            v.co.y *= max(d, 0.6) * 1.05
        A._place(ped, V(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, 0.0)))
        P.col(ped, P.p.material("pedestal"), 0.35, kind=K_DETAIL)
        MU.paint_corners(ped, lambda co, n: (P.p.material("gold"), 1.0, 0.28, K_GOLD) if abs(co.z + 0.055) < 0.006 else None)
        parts.append(ped)
    j = MU.join(parts, spec.id)
    MU.set_origin_bottom_center(j)
    j.location = (0, 0, 0)
    MU.shade_smooth(j, None)
    MU.add_subsurf(j, 1, 1)
    j.data.materials.clear()
    j.data.materials.append(M.clay_gloss())
    for k, v in dict(head_center=(0.0, 0.0, -10.0), head_radius=1.0, face_yaw=0.0, eye_x=0.0, eye_z=0.0, eye_w=0.01,
                     eye_h=0.01, iris_scale=1.0, has_brow=0.0, has_lips=0.0, mark_z=0.0, moustache=0.0,
                     mark_type=0.0).items():
        j[k] = v
    pack_face_props(j)
    lo, hi = MU.bounds_local(j)
    j["hotspot_local"] = (0.0, 0.0, hi.z * 0.85)
    j.scale = (size, size, size)
    j["doll_id"] = spec.id
    j["step"] = spec.step
    j["slot"] = spec.position.slot
    j["archetype"] = "animal"
    j["unit_height"] = size
    for c in list(j.users_collection):
        c.objects.unlink(j)
    (collection or bpy.context.scene.collection).objects.link(j)
    return j


def make_doll(spec: DollSpec, cfg: GoluConfig, collection=None) -> bpy.types.Object:
    """SPEC §4.3 entry point: one joined, painted, varnished doll object (origin at pedestal bottom centre)."""
    if spec.archetype == "animal":
        return build_animal(spec, cfg, collection)
    if spec.archetype == "object":
        from . import props as PR
        return PR.build_golu_object(spec, cfg, collection)
    return build_figure(resolve_params(spec, cfg), collection)


def doll_footprint(obj: bpy.types.Object) -> tuple[float, float]:
    lo, hi = MU.bounds_world(obj)
    return (hi.x - lo.x, hi.y - lo.y)
