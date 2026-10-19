import { describe, expect, it, vi } from 'vitest';
vi.mock('../../src/lib/frames.json', () => ({ default: {} }));

import { coverFit, cropWidthFraction, frameToViewport, portraitFocusX } from '../../src/lib/engine/coverFit';
import { flamesAt, hotspotsAt } from '../../src/lib/engine/hotspots';
import { frameToProgress, progressToFrame, stepStartProgress, totalScrollPx } from '../../src/lib/engine/scrollMap';
import { FrameCache, decodeWindowFor } from '../../src/lib/engine/FrameCache';
import { frameUrl, globalOf, stepOfGlobal, stepProgress } from '../../src/lib/frames';
import { makeFrames } from './fixture';

const F = makeFrames();

describe('frames index', () => {
  it('totals 1128 frames with contiguous steps', () => {
    expect(F.totalFrames).toBe(1128);
    let expect_ = 0;
    for (const s of F.steps) {
      expect(s.globalStart).toBe(expect_);
      expect_ += s.count;
    }
  });
  it('maps global frames to steps and back', () => {
    expect(stepOfGlobal(0, F)).toEqual({ step: 1, local: 0 });
    expect(stepOfGlobal(119, F)).toEqual({ step: 1, local: 119 });
    expect(stepOfGlobal(120, F)).toEqual({ step: 2, local: 0 });
    expect(stepOfGlobal(1127, F)).toEqual({ step: 9, local: 167 });
    expect(stepOfGlobal(99999, F)).toEqual({ step: 9, local: 167 });
    expect(globalOf(3, 10, F)).toBe(250);
  });
  it('builds 1-based versioned frame urls', () => {
    expect(frameUrl(2, 0, 'desktop', F)).toBe('/frames/step2/f_0001.webp?v=test');
    expect(frameUrl(9, 167, 'mobile', F)).toBe('/frames-mobile/step9/f_0168.webp?v=test');
  });
  it('reports hold / transition / finale phases', () => {
    expect(stepProgress(48, F).phase).toBe('hold');
    expect(stepProgress(110, F).phase).toBe('transition');
    expect(stepProgress(1127, F)).toMatchObject({ step: 9, phase: 'finale', p: 1 });
  });
});

describe('scroll map', () => {
  it('maps 0 → 0 and 1 → last frame, monotonically', () => {
    expect(progressToFrame(0, 1128)).toBe(0);
    expect(progressToFrame(1, 1128)).toBe(1127);
    let prev = -1;
    for (let p = 0; p <= 1.0001; p += 0.001) {
      const f = progressToFrame(p, 1128);
      expect(f).toBeGreaterThanOrEqual(prev);
      prev = f;
    }
    expect(progressToFrame(Number.NaN, 1128)).toBe(0);
  });
  it('uses 40 frames per viewport height', () => {
    expect(totalScrollPx(1128, 1000)).toBe(28200);
  });
  it('navigator jumps land inside the hold, past the title-card fade-in', () => {
    const p = stepStartProgress(240, 95, 1128);
    const f = progressToFrame(p, 1128);
    expect(f).toBeGreaterThan(240 + 9);
    expect(f).toBeLessThan(240 + 20);
    expect(frameToProgress(1127, 1128)).toBe(1);
  });
});

describe('cover fit', () => {
  it('covers a wider viewport by cropping top/bottom', () => {
    const r = coverFit(1920, 1080, 2560, 1080);
    expect(r.sw).toBe(1920);
    expect(r.sh).toBeCloseTo(810);
    expect(r.sy).toBeCloseTo(135);
  });
  it('covers a portrait viewport by cropping the sides around focusX', () => {
    const r = coverFit(1920, 1080, 390, 844, 0.5);
    expect(r.sh).toBe(1080);
    expect(r.sw).toBeCloseTo(1080 * (390 / 844));
    expect(r.sx + r.sw / 2).toBeCloseTo(960);
    const left = coverFit(1920, 1080, 390, 844, 0);
    expect(left.sx).toBe(0);
    const right = coverFit(1920, 1080, 390, 844, 1);
    expect(right.sx + right.sw).toBeCloseTo(1920);
  });
  it('portrait pan stays inside the frame and sweeps left → right', () => {
    const crop = cropWidthFraction(1920, 1080, 390, 844);
    const xs = [0.1, 0.5, 0.92];
    const a = portraitFocusX(xs, crop, 0);
    const b = portraitFocusX(xs, crop, 1);
    expect(a).toBeLessThan(b);
    for (const v of [a, b]) {
      expect(v - crop / 2).toBeGreaterThanOrEqual(-1e-9);
      expect(v + crop / 2).toBeLessThanOrEqual(1 + 1e-9);
    }
    expect(portraitFocusX(xs, 1, 0.3)).toBe(0.5);
  });
  it('maps frame points into viewport pixels', () => {
    const r = coverFit(1920, 1080, 1920, 1080);
    expect(frameToViewport(0.5, 0.5, r, 1920, 1080)).toEqual([960, 540]);
  });
});

describe('hotspots', () => {
  it('interpolates tracks and hides during transitions', () => {
    const h = hotspotsAt(F, 1, 4);
    expect(h).toHaveLength(2);
    expect(h[0].x).toBeCloseTo(0.2 + 4 / 400, 5);
    expect(hotspotsAt(F, 1, 100)).toEqual([]);
    const late = hotspotsAt(F, 1, 90).find((x) => x.id === 's1_b');
    expect(late?.vis).toBe(false);
  });
  it('returns lamp flame positions', () => {
    expect(flamesAt(F, 2, 30)).toEqual([[0.1, 0.6], [0.9, 0.6]]);
  });
});

describe('FrameCache', () => {
  const fakeBitmap = () => ({ close: vi.fn(), width: 4, height: 4 }) as unknown as ImageBitmap;
  it('is never blank once placeholders are loaded, and frees far steps', async () => {
    const fetched: string[] = [];
    const cache = new FrameCache({
      variant: 'desktop',
      decodeWindow: 4,
      frames: F,
      fetcher: async (url) => {
        fetched.push(url);
        return new Blob(['x']);
      },
      decoder: async () => fakeBitmap(),
    });
    expect(cache.nearest(500)).toBeNull();
    await cache.preloadPlaceholders();
    expect(cache.hasPlaceholders()).toBe(true);
    for (const g of [0, 300, 777, 1127]) expect(cache.nearest(g)).not.toBeNull();
    cache.setPlayhead(10, 1);
    await new Promise((r) => setTimeout(r, 20));
    expect(cache.get(10)).not.toBeNull();
    expect(fetched.some((u) => u.includes('/step2/'))).toBe(true);      // the next step is prefetched
    cache.setPlayhead(1000, 1);
    await new Promise((r) => setTimeout(r, 20));
    expect(cache.stats().blobs).toBeGreaterThan(0);
    const steps = new Set<number>();
    for (let g = 0; g < 1128; g++) if (cache.get(g)) steps.add(stepOfGlobal(g, F).step);
    expect([...steps].every((s) => s >= 7)).toBe(true);                  // decoded window follows the playhead
    expect(cache.stats().blankDraws).toBe(0);                           // the pre-placeholder probe is not a visible blank
    cache.dispose();
  });
  it('sizes the decode window from device memory', () => {
    expect(decodeWindowFor(2, true)).toBe(6);
    expect(decodeWindowFor(8, true)).toBe(8);
    expect(decodeWindowFor(8, false)).toBe(16);
    expect(decodeWindowFor(undefined, true)).toBe(8);      // phones decode full-HD band frames (D68)
  });
});
