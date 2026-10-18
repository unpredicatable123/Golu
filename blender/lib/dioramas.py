"""Per-step dioramas: build every config doll, place it by slot, seat it on story props (SPEC §4.4)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import bpy
from mathutils import Matrix, Vector

from . import doll_factory as D
from . import mesh_utils as MU
from . import props as PR
from .config import DollSpec, GoluConfig, StepSpec, rng_for
from .environment import StepHandle

SEAT_PROPS = {"launch_pad", "lunar_patch", "rail_track", "metro_viaduct", "plinth", "rice_mound", "paran_platform"}
CLOTH = 0.0025      # silk drape thickness on the tread


@dataclass
class Placed:
    spec: DollSpec
    obj: bpy.types.Object
    base: Vector                  # world position of the doll origin
    yaw: float
    seat_obj: bpy.types.Object | None = None
    anchored: bool = False


@dataclass
class StepResult:
    step: StepSpec
    handle: StepHandle
    placed: list[Placed] = field(default_factory=list)
    props: list[bpy.types.Object] = field(default_factory=list)


def slot_world(handle: StepHandle, spec: DollSpec, layout: dict, rng) -> tuple[Vector, float]:
    x = spec.position.x * handle.usable / 2 + rng.uniform(-0.012, 0.012)
    y = handle.front_line(spec.position.row, layout)
    yaw = math.radians(spec.position.turn + rng.uniform(-3.0, 3.0))
    return Vector((x, y, handle.z_top + CLOTH)), yaw


def _put(obj: bpy.types.Object, loc: Vector, yaw: float) -> None:
    s = obj.scale.copy()
    obj.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Diagonal((*s, 1.0))


def _link(obj, col):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def build_step(cfg: GoluConfig, step: StepSpec, handle: StepHandle, dolls_col, props_col,
               only: set[str] | None = None) -> StepResult:
    res = StepResult(step=step, handle=handle)
    Pl = PR._Pal(cfg.palette)
    for spec in step.dolls:
        if only and spec.id not in only:
            continue
        rng = rng_for("place", spec.id)
        obj = D.make_doll(spec, cfg, dolls_col)
        loc, yaw = slot_world(handle, spec, cfg.layout, rng)
        res.placed.append(Placed(spec=spec, obj=obj, base=loc, yaw=yaw))
    by_id = {p.spec.id: p for p in res.placed}

    # --- seat props under single dolls
    for p in res.placed:
        if p.spec.seat in SEAT_PROPS:
            lo, hi = MU.bounds_local(p.obj)
            width = (hi.x - lo.x) * (p.obj.scale.x if p.spec.archetype != "object" else 1.0)
            seat, top = PR.build_seat_prop(p.spec.seat, Pl, rng_for("seat", p.spec.id), width=max(width, 0.12))
            _link(seat, props_col)
            _put(seat, p.base.copy(), p.yaw)
            p.seat_obj = seat
            p.base.z += top
            res.props.append(seat)

    # --- story props (sets) per step
    sid = step.id
    if sid == 1 and "s1_pslv" in by_id:
        r = by_id["s1_pslv"]
        g = _link(PR.build_rocket_gantry(Pl, rng_for("gantry")), props_col)
        _put(g, r.base + Vector((-0.09, 0.03, -0.037 + 0.025)), math.pi)
        res.props.append(g)
    if sid == 3 and "s3_rama" in by_id and "s3_sita" in by_id:
        a, b = by_id["s3_rama"], by_id["s3_sita"]
        cx = (a.base.x + b.base.x) / 2
        a.base.x, b.base.x = cx - 0.085, cx + 0.085
        m = _link(PR.build_mandapam(Pl, rng_for("mandapam")), props_col)
        _put(m, Vector((cx, handle.front_line("front", cfg.layout) + 0.01, handle.z_top + CLOTH)), 0.0)
        res.props.append(m)
    if sid == 4 and "s4_valli" in by_id:
        v = by_id["s4_valli"]
        f = _link(PR.build_thinai_field(Pl, rng_for("thinai")), props_col)
        _put(f, Vector((v.base.x + 0.05, handle.y_front + 0.17, handle.z_top + CLOTH)), 0.0)
        res.props.append(f)
        plat, top = PR.build_seat_prop("paran_platform", Pl, rng_for("paran"))
        _link(plat, props_col)
        _put(plat, Vector((v.base.x, v.base.y, handle.z_top + CLOTH)), 0.0)
        v.base.z = handle.z_top + CLOTH + top
        res.props.append(plat)
    if sid == 5:
        seated = [by_id[i] for i in ("s5_chettiar", "s5_chettichi") if i in by_id]
        if seated:
            cx = sum(p.base.x for p in seated) / len(seated)
            shop, floor_h = PR.build_chettiar_shop(Pl, rng_for("shop"))
            _link(shop, props_col)
            _put(shop, Vector((cx, handle.y_front + 0.17, handle.z_top + CLOTH)), 0.0)
            res.props.append(shop)
            for p in seated:
                p.base.y = handle.y_front + 0.15
                p.base.z = handle.z_top + CLOTH + floor_h
        if "s5_potter" in by_id:
            pots = _link(PR.build_drying_pots(Pl, rng_for("pots")), props_col)
            q = by_id["s5_potter"]
            _put(pots, Vector((q.base.x + 0.1, handle.y_front + 0.25, handle.z_top + CLOTH)), 0.0)
            res.props.append(pots)
    if sid == 7:
        if "s7_kaliya_krishna" in by_id:
            k = by_id["s7_kaliya_krishna"]
            kal, top = PR.build_kaliya(Pl, rng_for("kaliya"))
            _link(kal, props_col)
            _put(kal, Vector((k.base.x, k.base.y + 0.03, handle.z_top + CLOTH)), 0.0)
            k.base.z = handle.z_top + CLOTH + top - 0.012
            k.base.y += 0.02
            res.props.append(kal)
        if "s7_govardhana_krishna" in by_id:
            g = by_id["s7_govardhana_krishna"]
            res.props.append(("govardhana", g))   # placed after the doll transform is final (fingertip)

    # --- final transforms, overlap relaxation, anchored riders/drivers
    _relax(res, cfg)
    for p in res.placed:
        _put(p.obj, p.base, p.yaw)
    if sid == 5 and "s5_cart_driver" in by_id and "s5_bullock_cart" in by_id:
        cart, drv = by_id["s5_bullock_cart"], by_id["s5_cart_driver"]
        bpy.context.view_layer.update()
        anchor = cart.obj.matrix_world @ Vector(cart.obj["anchor_cart_yoke"])   # matrix includes the cart scale
        _put(drv.obj, anchor - Vector((0, 0, 0.0)), cart.yaw + math.radians(-90))
        drv.base, drv.anchored = anchor, True
    out_props = []
    for pr in res.props:
        if isinstance(pr, tuple) and pr[0] == "govardhana":
            g = pr[1]
            bpy.context.view_layer.update()
            # lifted left hand (doll units): wrist z 1.05 + finger 0.067, shifted +0.05 by the pedestal in finalize
            tip = g.obj.matrix_world @ Vector((0.09, -0.02, 1.05 + 0.067 + 0.05))
            hill = _link(PR.build_govardhana(Pl, rng_for("govardhana")), props_col)
            _put(hill, Vector((tip.x + 0.08, tip.y + 0.03, tip.z - 0.012)), 0.0)   # finger sinks into the hill's underside
            out_props.append(hill)
        else:
            out_props.append(pr)
    res.props = out_props
    if step.id in TRINKET_STEPS:
        res.props += _dress_tread(res, cfg, Pl, props_col)
    return res


TRINKET_STEPS = {6, 8}       # lineup steps without a story set: dress the gaps between dolls


def _dress_tread(res: StepResult, cfg: GoluConfig, Pl, props_col) -> list[bpy.types.Object]:
    """Place a small brass pooja item in every front-row gap wider than 0.1 m, just ahead of the dolls."""
    bpy.context.view_layer.update()
    front = sorted((p for p in res.placed if p.spec.position.row == "front" and not p.anchored),
                   key=lambda p: p.obj.matrix_world.translation.x)
    out = []
    y = res.handle.front_line("front", cfg.layout) - 0.045
    for i, (a, b) in enumerate(zip(front, front[1:])):
        gap_lo, gap_hi = footprint(a.obj)[1].x, footprint(b.obj)[0].x
        gap = gap_hi - gap_lo
        if gap < 0.1:
            continue
        kind = PR.TRINKETS[(i + res.step.id) % len(PR.TRINKETS)]
        if gap < 0.14 and kind == "flower_plate":      # the plate is the widest item
            kind = "kindi" if i % 2 else "kumkum_pair"
        t = PR.build_tread_trinket(kind, Pl, rng_for("trinket", res.step.id, i), f"trinket_{res.step.id}_{i}")
        _link(t, props_col)
        t.scale = (1.3, 1.3, 1.3)        # read at camera distance next to 0.2 m dolls
        t.location = ((gap_lo + gap_hi) / 2, y, res.handle.z_top + CLOTH)
        out.append(t)
    return out


def _relax(res: StepResult, cfg: GoluConfig) -> None:
    """1-D relaxation per row: keep slot order, push apart until bounding boxes have ≥ 6 mm gaps."""
    for row in ("front", "back"):
        items = [p for p in res.placed if p.spec.position.row == row and p.spec.seat not in ("cart_yoke",)]
        items.sort(key=lambda p: p.spec.position.slot)
        half = []
        for p in items:
            lo, hi = MU.bounds_local(p.obj)
            sx = p.obj.scale.x
            half.append(((hi.x - lo.x) * sx / 2) * 0.92)
        for _ in range(40):
            moved = False
            for i in range(len(items) - 1):
                a, b = items[i], items[i + 1]
                gap = (b.base.x - half[i + 1]) - (a.base.x + half[i])
                if gap < 0.006 and not (a.spec.id in ("s3_rama",) and b.spec.id == "s3_sita"):
                    push = (0.006 - gap) / 2
                    a.base.x -= push
                    b.base.x += push
                    moved = True
            if not moved:
                break
        lim = res.handle.width / 2 - 0.02
        for p, h in zip(items, half):
            p.base.x = max(-lim + h, min(lim - h, p.base.x))


def build_all(cfg: GoluConfig, steps: list[StepHandle], only: set[str] | None = None) -> list[StepResult]:
    dolls_col = MU.ensure_collection("Dolls")
    props_col = MU.ensure_collection("StoryProps")
    out = []
    for handle in steps:
        step = cfg.step(handle.n)
        out.append(build_step(cfg, step, handle, dolls_col, props_col, only))
    return out


def footprint(obj: bpy.types.Object) -> tuple[Vector, Vector]:
    """World-space XY extent of the bottom 30% of a doll (pedestal/feet), ignoring raised arms and fans."""
    lo, hi = MU.bounds_local(obj)
    cut = lo.z + (hi.z - lo.z) * 0.3
    mw = obj.matrix_world
    pts = [mw @ v.co for v in obj.data.vertices if v.co.z <= cut]
    if not pts:
        return MU.bounds_world(obj)
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), 0)),
            Vector((max(p.x for p in pts), max(p.y for p in pts), 0)))


def verify_placement(cfg: GoluConfig, results: list[StepResult]) -> list[str]:
    errs = []
    built = {p.spec.id for r in results for p in r.placed}
    for d in cfg.all_dolls():
        if d.id not in built:
            errs.append(f"{d.id}: not built")
    for r in results:
        h = r.handle
        xs = [(p.spec.position.slot, p.obj.matrix_world.translation.x, p.spec.position.row, p.spec.id)
              for p in r.placed if not p.anchored]
        for row in ("front", "back"):
            seq = sorted([x for x in xs if x[2] == row])
            for a, b in zip(seq, seq[1:]):
                if b[1] < a[1] - 0.01:
                    errs.append(f"step {h.n}: {b[3]} left of {a[3]} (slot order broken)")
        for p in r.placed:
            loc = p.obj.matrix_world.translation
            if not (-h.width / 2 <= loc.x <= h.width / 2):
                errs.append(f"{p.spec.id}: x {loc.x:.3f} outside tier width")
            if not (h.y_front - 0.02 <= loc.y <= h.y_back + 0.02):
                errs.append(f"{p.spec.id}: y {loc.y:.3f} outside tread")
            if loc.z < h.z_top - 0.005:
                errs.append(f"{p.spec.id}: below tread top")
        feet = {p.spec.id: footprint(p.obj) for p in r.placed}
        for i, a in enumerate(r.placed):
            la, ha = feet[a.spec.id]
            for b in r.placed[i + 1:]:
                if a.anchored or b.anchored or {a.spec.id, b.spec.id} == {"s5_cow", "s5_calf"}:
                    continue
                lb, hb = feet[b.spec.id]
                ox = min(ha.x, hb.x) - max(la.x, lb.x)
                oy = min(ha.y, hb.y) - max(la.y, lb.y)
                if ox > 0 and oy > 0:
                    area = ox * oy
                    small = min((ha.x - la.x) * (ha.y - la.y), (hb.x - lb.x) * (hb.y - lb.y))
                    if small > 0 and area / small > 0.35:
                        errs.append(f"step {h.n}: {a.spec.id} overlaps {b.spec.id} ({area / small:.0%})")
    return errs
