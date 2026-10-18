import type { FramesJson, StepFrames } from '../../src/lib/frames';

/** Synthetic frames.json with the real layout: 8 × (96 hold + 24 transition) + (96 hold + 72 finale) = 1128. */
export function makeFrames(): FramesJson {
  const steps: StepFrames[] = [];
  let start = 0;
  for (let id = 1; id <= 9; id++) {
    const count = id < 9 ? 120 : 168;
    const sampleFrames = [0, 8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 95];
    steps.push({
      id,
      dir: `step${id}`,
      count,
      globalStart: start,
      hold: [0, 95],
      transition: id < 9 ? [96, 119] : null,
      finale: id === 9 ? [96, 167] : null,
      keyFrame: 47,
      sampleFrames,
      bytes: { desktop: 1, mobile: 1 },
      hotspots: {
        [`s${id}_a`]: { every: 8, t: sampleFrames.map((f) => [0.2 + f / 400, 0.5, 1] as [number, number, number]) },
        [`s${id}_b`]: { every: 8, t: sampleFrames.map((f) => [0.7 + f / 400, 0.45, f < 48 ? 1 : 0] as [number, number, number]) },
      },
      flames: { every: 8, t: sampleFrames.map(() => [[0.1, 0.6], [0.9, 0.6]] as Array<[number, number]>) },
    });
    start += count;
  }
  return {
    version: 'test',
    fps: 24,
    totalFrames: start,
    desktop: { width: 1920, height: 1080, dir: 'frames' },
    mobile: { width: 960, height: 540, dir: 'frames-mobile' },
    doors: { count: 72 },
    steps,
  };
}
