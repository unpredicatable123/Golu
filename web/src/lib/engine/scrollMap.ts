// Scroll ↔ frame mapping (DECISIONS D45): a constant number of frames per viewport height of scroll.
export const FRAMES_PER_VH = 40;

export function totalScrollPx(totalFrames: number, viewportH: number, framesPerVh = FRAMES_PER_VH): number {
  return Math.round((totalFrames / framesPerVh) * viewportH);
}

/** Scroll progress 0..1 → global frame index (0-based), clamped and rounded. */
export function progressToFrame(progress: number, totalFrames: number): number {
  const p = Math.min(1, Math.max(0, Number.isFinite(progress) ? progress : 0));
  return Math.round(p * (totalFrames - 1));
}

export function frameToProgress(frame: number, totalFrames: number): number {
  return Math.min(1, Math.max(0, frame / Math.max(1, totalFrames - 1)));
}

/** Progress a navigator jump lands on: 12% into the step's hold, so its title card is already visible. */
export function stepStartProgress(globalStart: number, holdEnd: number, totalFrames: number): number {
  return frameToProgress(globalStart + Math.round(holdEnd * 0.12), totalFrames);
}
