"""QA helpers: image statistics, warmth checks, QA cameras, contact sheets and sprite alpha reports."""
from __future__ import annotations

import colorsys
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

from . import render as R


def load_rgba(path: Path) -> np.ndarray:
    """Returns float32 HxWx4 array, top row first, values as stored (sRGB-encoded 0..1)."""
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1]


def save_rgba(arr: np.ndarray, path: Path) -> Path:
    h, w = arr.shape[:2]
    img = bpy.data.images.new(Path(path).stem, w, h, alpha=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(np.ascontiguousarray(arr[::-1]).astype(np.float32).ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save()
    bpy.data.images.remove(img)
    return Path(path)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def image_stats(path: Path) -> dict:
    a = load_rgba(path)[..., :3]
    lum = _luma(a)
    clipped = np.mean(np.all(a >= 0.995, axis=-1))
    void = np.mean(lum < 0.004)
    thr = np.quantile(lum, 0.99)
    hi = a[lum >= thr]
    hr, hg, hb = (float(x) for x in hi.mean(axis=0))
    hue = colorsys.rgb_to_hsv(hr, hg, hb)[0] * 360.0
    rb = float(a[..., 0].mean() / max(a[..., 2].mean(), 1e-4))
    return {"mean_luma": float(lum.mean()), "r_over_b": rb, "clipped_pct": float(clipped * 100),
            "void_pct": float(void * 100), "highlight_hue": hue, "p99_luma": float(thr)}


def assert_warm(stats: dict) -> list[str]:
    errs = []
    if not 0.10 <= stats["mean_luma"] <= 0.38:
        errs.append(f"mean luminance {stats['mean_luma']:.3f} outside 0.10–0.38")
    if stats["r_over_b"] < 1.45:
        errs.append(f"R/B {stats['r_over_b']:.2f} < 1.45 (not warm enough)")
    if stats["clipped_pct"] > 0.1:
        errs.append(f"{stats['clipped_pct']:.2f}% clipped white (> 0.1%)")
    if not 20 <= stats["highlight_hue"] <= 55:
        errs.append(f"highlight hue {stats['highlight_hue']:.0f}° outside 20–55°")
    if stats["void_pct"] > 8:
        errs.append(f"{stats['void_pct']:.1f}% black void (> 8%)")
    return errs


def look_at(loc: Vector, target: Vector, roll: float = 0.0) -> Matrix:
    loc, target = Vector(loc), Vector(target)
    d = (target - loc).normalized()
    rot = d.to_track_quat("-Z", "Y").to_matrix().to_4x4()
    if roll:
        rot = rot @ Matrix.Rotation(roll, 4, "Z")
    return Matrix.Translation(loc) @ rot


def qa_cameras(layout: dict) -> dict[str, Matrix]:
    rise, tread = layout["rise"], layout["tread"]
    n = layout["step_count"]
    top = n * rise
    y1 = -(n - 1) * tread
    return {
        "establishing": look_at(Vector((0.0, y1 - 4.9, 1.30)), Vector((0.0, -1.9, 0.82))),
        "step1": look_at(Vector((0.0, y1 - 1.75, rise + 0.32)), Vector((0.0, y1 + 0.1, rise + 0.10))),
        "step9": look_at(Vector((0.0, -1.55, top + 0.30)), Vector((0.0, 0.0, top + 0.12))),
        "lamp": look_at(Vector((-1.05, y1 - 1.25, 1.05)), Vector((-1.72, y1 - 0.15, 0.78))),
        "kolam": look_at(Vector((0.0, y1 - 2.95, 1.25)), Vector((0.0, y1 - 1.3, 0.0))),
    }


def ensure_qa_camera(scene: bpy.types.Scene, lens: float = 40.0) -> bpy.types.Object:
    cam = bpy.data.objects.get("CAM_QA")
    if cam is None:
        cam = bpy.data.objects.new("CAM_QA", bpy.data.cameras.new("CAM_QA"))
        scene.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.sensor_width = 36
    cam.data.clip_start = 0.02
    cam.data.clip_end = 60
    return cam


def render_stills(scene: bpy.types.Scene, views: dict[str, Matrix], out_dir: Path, prefix: str = "") -> list[Path]:
    cam = ensure_qa_camera(scene)
    prev = scene.camera
    scene.camera = cam
    out = []
    for name, mat in views.items():
        cam.matrix_world = mat
        p = Path(out_dir) / f"{prefix}{name}.png"
        secs = R.render_still(scene, p)
        R.log(f"rendered {p.name} in {secs:.1f}s")
        out.append(p)
    scene.camera = prev or cam
    return out


def contact_sheet(paths: list[Path], cols: int, out: Path, thumb: int = 384, bg=(0.06, 0.03, 0.02)) -> Path:
    tiles = []
    for p in paths:
        a = load_rgba(p)
        h, w = a.shape[:2]
        s = thumb / max(h, w)
        nh, nw = max(1, int(h * s)), max(1, int(w * s))
        ys = (np.arange(nh) / s).astype(int).clip(0, h - 1)
        xs = (np.arange(nw) / s).astype(int).clip(0, w - 1)
        t = a[ys][:, xs]
        if t.shape[2] == 4:
            alpha = t[..., 3:4]
            t = np.concatenate([t[..., :3] * alpha + np.array(bg) * (1 - alpha), np.ones_like(alpha)], axis=-1)
        tiles.append(t)
    th = max(t.shape[0] for t in tiles)
    tw = max(t.shape[1] for t in tiles)
    rows = math.ceil(len(tiles) / cols)
    sheet = np.zeros((rows * th, cols * tw, 4), dtype=np.float32)
    sheet[..., :3] = bg
    sheet[..., 3] = 1
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        sheet[r * th:r * th + t.shape[0], c * tw:c * tw + t.shape[1]] = t
    return save_rgba(sheet, out)


def _islands(mask: np.ndarray) -> list[int]:
    """Connected-component sizes (4-connectivity) of a boolean mask, iterative flood fill."""
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    sizes = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]:
            continue
        stack = [(y0, x0)]
        seen[y0, x0] = True
        n = 0
        while stack:
            y, x = stack.pop()
            n += 1
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True
                    stack.append((yy, xx))
        sizes.append(n)
    return sorted(sizes, reverse=True)


def alpha_report(path: Path) -> dict:
    a = load_rgba(path)
    alpha = a[..., 3]
    border = np.concatenate([alpha[:2].ravel(), alpha[-2:].ravel(), alpha[:, :2].ravel(), alpha[:, -2:].ravel()])
    small = alpha[::2, ::2] > 0.02
    islands = [s for s in _islands(small) if s * 4 > 50]
    lum = _luma(a[..., :3])
    # semi-transparent edge pixels; black shadow-catcher pixels are a soft shadow, not an edge halo
    semi = (alpha > 0.05) & (alpha < 0.95) & (lum > 0.03)
    opaque = alpha >= 0.95
    fringe = 0.0
    if semi.any() and opaque.any():
        # neighbour-opaque mean luminance via 3x3 box over opaque pixels
        op = opaque.astype(np.float32)
        lo = lum * op
        k = np.ones((3, 3), dtype=np.float32)

        def box(x):
            p = np.pad(x, 1)
            return sum(p[i:i + x.shape[0], j:j + x.shape[1]] * k[i, j] for i in range(3) for j in range(3))

        cnt = box(op)
        nb = np.where(cnt > 0, box(lo) / np.maximum(cnt, 1), np.nan)
        sel = semi & (cnt > 0)
        if sel.any():
            unpremul = lum[sel]  # PNG from Blender is straight alpha already
            fringe = float(np.nanmean(np.abs(unpremul - nb[sel])))
    return {"border_max_alpha": float(border.max()), "islands": len(islands), "island_sizes": islands[:5],
            "fringe_dl": fringe, "coverage": float((alpha > 0.5).mean())}
