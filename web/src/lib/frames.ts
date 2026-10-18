// Frame index helpers over the generated frames.json (scripts/build_frames_json.mjs, DECISIONS D27).
import data from './frames.json';

export type Variant = 'desktop' | 'mobile';
export interface HotspotTrack { every: number; t: Array<[number, number, number]> }
export interface StepFrames {
  id: number;
  dir: string;
  count: number;
  globalStart: number;
  hold: [number, number];
  transition: [number, number] | null;
  finale: [number, number] | null;
  keyFrame: number;
  sampleFrames: number[];
  bytes: { desktop: number; mobile: number };
  hotspots: Record<string, HotspotTrack>;
  flames: { every: number; t: Array<Array<[number, number]>> };
}
export interface FramesJson {
  version: string;
  fps: number;
  totalFrames: number;
  desktop: { width: number; height: number; dir: string };
  mobile: { width: number; height: number; dir: string };
  doors: { count: number };
  /** audio files present in static/audio at encode time (others are synthesised) */
  audio?: string[];
  steps: StepFrames[];
}

export const frames = data as unknown as FramesJson;

/** Global (0-based) frame → step id (1-based) and local index (0-based) inside stepN/. */
export function stepOfGlobal(g: number, f: FramesJson = frames): { step: number; local: number } {
  const clamped = Math.max(0, Math.min(f.totalFrames - 1, Math.round(g)));
  for (const s of f.steps) {
    if (clamped < s.globalStart + s.count) return { step: s.id, local: clamped - s.globalStart };
  }
  const last = f.steps[f.steps.length - 1];
  return { step: last.id, local: last.count - 1 };
}

export function globalOf(step: number, local: number, f: FramesJson = frames): number {
  return f.steps[step - 1].globalStart + local;
}

/** /frames[-mobile]/stepN/f_0001.webp?v=… (files are 1-based). */
export function frameUrl(step: number, local: number, variant: Variant, f: FramesJson = frames): string {
  const dir = variant === 'desktop' ? f.desktop.dir : f.mobile.dir;
  const n = String(local + 1).padStart(4, '0');
  return `/${dir}/step${step}/f_${n}.webp?v=${f.version}`;
}

/** Where a global frame sits inside its step: hold (with 0..1 progress), transition, or finale. */
export function stepProgress(g: number, f: FramesJson = frames): { step: number; p: number; phase: 'hold' | 'transition' | 'finale' } {
  const { step, local } = stepOfGlobal(g, f);
  const s = f.steps[step - 1];
  if (local <= s.hold[1]) return { step, p: local / Math.max(1, s.hold[1]), phase: 'hold' };
  if (s.finale && local >= s.finale[0]) return { step, p: (local - s.finale[0]) / Math.max(1, s.finale[1] - s.finale[0]), phase: 'finale' };
  const tr = s.transition as [number, number];
  return { step, p: (local - tr[0]) / Math.max(1, tr[1] - tr[0]), phase: 'transition' };
}
