// Aarthi / camphor plate path (SPEC §5.3): exactly `cw` clockwise circles, then `ccw` anticlockwise circles,
// constant angular speed (one circle per `secPerCircle`), eased to rest at the reversal. Screen space: y points
// down, so increasing angle is clockwise as the viewer sees it (DECISIONS D40). The angle is the source of truth;
// the plate position and the bell strikes are derived from it, so the turn count is exact.

export interface OrbitSpec {
  cw: number;
  ccw: number;
  secPerCircle: number;
  reversalEase: number;   // fraction of a circle eased on each side of the reversal
  startDeg: number;       // 90° = bottom of the ellipse
}

/** f(u): identity with a quadratic ease-out over the last `a` of the range (slope 1 → 0), normalised to 1. */
function easeOutTail(u: number, a: number): number {
  const x = Math.min(1, Math.max(0, u));
  const u0 = 1 - a;
  const raw = x <= u0 ? x : u0 + (x - u0) - ((x - u0) * (x - u0)) / (2 * a);
  return raw / (1 - a / 2);
}

function phaseDuration(circles: number, s: OrbitSpec): number {
  const a = Math.min(0.9, s.reversalEase / Math.max(circles, 1e-6));
  return (circles * s.secPerCircle) / (1 - a / 2);
}

export function orbitDuration(s: OrbitSpec): number {
  return phaseDuration(s.cw, s) + phaseDuration(s.ccw, s);
}

/** Cumulative signed travel in degrees at time t (clockwise positive). Peaks at 360·cw, ends at 360·(cw − ccw). */
export function orbitTravel(t: number, s: OrbitSpec): number {
  const d1 = phaseDuration(s.cw, s);
  const d2 = phaseDuration(s.ccw, s);
  const a1 = Math.min(0.9, s.reversalEase / Math.max(s.cw, 1e-6));
  const a2 = Math.min(0.9, s.reversalEase / Math.max(s.ccw, 1e-6));
  if (t <= 0) return 0;
  if (t < d1) return 360 * s.cw * easeOutTail(t / d1, a1);
  const v = Math.min(1, (t - d1) / d2);
  const back = 1 - easeOutTail(1 - v, a2);        // starts from rest, then constant speed
  return 360 * s.cw - 360 * s.ccw * back;
}

/** Absolute screen angle (degrees) of the plate at time t. */
export function orbitAngle(t: number, s: OrbitSpec): number {
  return s.startDeg + orbitTravel(t, s);
}

export function ellipsePoint(angleDeg: number, cx: number, cy: number, rx: number, ry: number): [number, number] {
  const a = (angleDeg * Math.PI) / 180;
  return [cx + rx * Math.cos(a), cy + ry * Math.sin(a)];
}

/** Count completed signed turns from sampled travel (used by tests and the runtime ritual log). */
export function countTurns(samples: number[]): { cwTurns: number; ccwTurns: number } {
  let peak = 0;
  for (const v of samples) peak = Math.max(peak, v);
  const end = samples[samples.length - 1] ?? 0;
  return { cwTurns: Math.round(peak / 360), ccwTurns: Math.round((peak - end) / 360) };
}
