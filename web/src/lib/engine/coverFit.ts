// Cover-fit of a 16:9 frame into any viewport, with a horizontal focus for portrait screens (DECISIONS D37).
export interface Rect { sx: number; sy: number; sw: number; sh: number; dx: number; dy: number; dw: number; dh: number }

/** Source crop so the frame covers dst completely; focusX (0..1) chooses which horizontal slice stays visible. */
export function coverFit(srcW: number, srcH: number, dstW: number, dstH: number, focusX = 0.5): Rect {
  const srcAspect = srcW / srcH;
  const dstAspect = dstW / dstH;
  let sw = srcW;
  let sh = srcH;
  if (dstAspect > srcAspect) sh = srcW / dstAspect;
  else sw = srcH * dstAspect;
  const fx = Math.min(1, Math.max(0, focusX));
  const sx = Math.min(srcW - sw, Math.max(0, fx * srcW - sw / 2));
  const sy = (srcH - sh) / 2;
  return { sx, sy, sw, sh, dx: 0, dy: 0, dw: dstW, dh: dstH };
}

/** Visible width of the frame (fraction 0..1) for a viewport; < 1 means the sides are cropped. */
export function cropWidthFraction(srcW: number, srcH: number, dstW: number, dstH: number): number {
  return Math.min(1, (dstW / dstH) / (srcW / srcH));
}

/**
 * Portrait pan: sweep the crop window across the step's dolls as the hold progresses (p 0..1), from the
 * leftmost visible hotspot to the rightmost, clamped so the crop stays inside the frame.
 */
export function portraitFocusX(hotspotXs: number[], cropW: number, p: number): number {
  if (cropW >= 1) return 0.5;
  const half = cropW / 2;
  if (!hotspotXs.length) return 0.5;
  const lo = Math.min(...hotspotXs) + half * 0.6;
  const hi = Math.max(...hotspotXs) - half * 0.6;
  const t = p < 0 ? 0 : p > 1 ? 1 : p;
  const eased = t * t * (3 - 2 * t);
  const x = hi > lo ? lo + (hi - lo) * eased : (lo + hi) / 2;
  return Math.min(1 - half, Math.max(half, x));
}

/** Frame-space point (0..1, top-left origin) → viewport pixels for a given cover rect. */
export function frameToViewport(x: number, y: number, r: Rect, srcW: number, srcH: number): [number, number] {
  const px = x * srcW;
  const py = y * srcH;
  return [((px - r.sx) / r.sw) * r.dw + r.dx, ((py - r.sy) / r.sh) * r.dh + r.dy];
}
