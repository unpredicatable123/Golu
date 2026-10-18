// Hotspot & lamp-flame tracks sampled every N frames by camera.py, linearly interpolated (DECISIONS D38, D39).
import type { FramesJson, StepFrames } from '../frames';

export interface Hotspot { id: string; x: number; y: number; vis: boolean }

function sampleIndex(s: StepFrames, local: number): { i: number; t: number } {
  const sf = s.sampleFrames;
  if (local <= sf[0]) return { i: 0, t: 0 };
  for (let i = 0; i < sf.length - 1; i++) {
    if (local <= sf[i + 1]) return { i, t: (local - sf[i]) / Math.max(1, sf[i + 1] - sf[i]) };
  }
  return { i: sf.length - 1, t: 0 };
}

/** Hotspots of a step at a local frame; hidden outside the hold (transitions and finale). */
export function hotspotsAt(f: FramesJson, step: number, local: number): Hotspot[] {
  const s = f.steps[step - 1];
  if (!s || local > s.hold[1]) return [];
  const { i, t } = sampleIndex(s, local);
  const out: Hotspot[] = [];
  for (const [id, tr] of Object.entries(s.hotspots)) {
    const a = tr.t[i];
    const b = tr.t[Math.min(i + 1, tr.t.length - 1)];
    if (!a) continue;
    const vis = t < 0.5 ? a[2] === 1 : b[2] === 1;
    out.push({ id, x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, vis });
  }
  return out;
}

/** Projected kuthuvilakku/agal flame positions at a local frame (hold samples only; nearest sample). */
export function flamesAt(f: FramesJson, step: number, local: number): Array<[number, number]> {
  const s = f.steps[step - 1];
  if (!s || !s.flames.t.length) return [];
  const { i, t } = sampleIndex(s, Math.min(local, s.hold[1]));
  const a = s.flames.t[i] ?? [];
  const b = s.flames.t[Math.min(i + 1, s.flames.t.length - 1)] ?? a;
  if (a.length !== b.length) return t < 0.5 ? a : b;
  return a.map((p, k) => [p[0] + (b[k][0] - p[0]) * t, p[1] + (b[k][1] - p[1]) * t]);
}
