// Two-tier frame cache (SPEC §5.2, DECISIONS D36).
//  • fetch tier: compressed WebP Blobs for the current step + the next; steps more than 2 away are freed
//  • decode tier: ImageBitmaps (createImageBitmap) in a window around the playhead, biased in scroll direction
//  • placeholders: each step's first frame (mobile size), decoded and kept forever → the canvas is never blank
import { frameUrl, frames as defaultFrames, stepOfGlobal, type FramesJson, type Variant } from '../frames';

export interface CacheStats { blobs: number; bitmaps: number; fallbacks: number; blankDraws: number; frame: number }

type Fetcher = (url: string) => Promise<Blob>;
type Decoder = (blob: Blob) => Promise<ImageBitmap>;

export class FrameCache {
  private blobs = new Map<number, Blob>();
  private bitmaps = new Map<number, ImageBitmap>();
  private placeholders = new Map<number, ImageBitmap>();
  private inflight = new Map<number, Promise<void>>();
  private decoding = new Set<number>();
  private queue: number[] = [];
  private active = 0;
  private playhead = 0;
  private direction: 1 | -1 = 1;
  private disposed = false;
  readonly counters = { fallbacks: 0, blankDraws: 0 };
  /** placeholders loaded; before this the entrance covers the canvas, so a miss is not a visible blank */
  private primed = false;

  constructor(
    private opts: {
      variant: Variant;
      decodeWindow: number;
      maxConcurrent?: number;
      frames?: FramesJson;
      fetcher?: Fetcher;
      decoder?: Decoder;
      onReady?: (global: number) => void;
    }
  ) {}

  private get f(): FramesJson {
    return this.opts.frames ?? defaultFrames;
  }

  private fetchBlob: Fetcher = async (url) => {
    if (this.opts.fetcher) return this.opts.fetcher(url);
    const res = await fetch(url, { cache: 'force-cache' });
    if (!res.ok) throw new Error(`${res.status} ${url}`);
    return res.blob();
  };

  private decode: Decoder = (blob) => (this.opts.decoder ? this.opts.decoder(blob) : createImageBitmap(blob));

  /** Canvas size in device pixels: frames are decoded straight to their cover-fit draw size, off the main
   *  thread, so each draw is a cheap 1:1 copy instead of a high-quality downscale (smooth scrubbing). */
  private drawSize: { w: number; h: number } | null = null;

  setDrawSize(w: number, h: number): void {
    if (this.drawSize && this.drawSize.w === w && this.drawSize.h === h) return;
    this.drawSize = { w, h };
    for (const b of this.bitmaps.values()) b.close();      // re-decode the window at the new size
    this.bitmaps.clear();
    this.decodeWindow();
  }

  private decodeFrame(blob: Blob): Promise<ImageBitmap> {
    if (this.opts.decoder || !this.drawSize) return this.decode(blob);
    const v = this.opts.variant === 'desktop' ? this.f.desktop : this.f.mobile;
    const scale = Math.max(this.drawSize.w / v.width, this.drawSize.h / v.height);
    if (scale >= 0.95) return this.decode(blob);
    return createImageBitmap(blob, {
      resizeWidth: Math.round(v.width * scale),
      resizeHeight: Math.round(v.height * scale),
      resizeQuality: 'high',
    });
  }

  /** First frame of every step at mobile size: tiny, decoded once, never evicted (the last-resort fallback). */
  async preloadPlaceholders(onProgress?: (done: number, total: number) => void): Promise<void> {
    const steps = this.f.steps;
    let done = 0;
    await Promise.all(
      steps.map(async (s) => {
        const blob = await this.fetchBlob(frameUrl(s.id, 0, 'mobile', this.f));
        this.placeholders.set(s.id, await this.decode(blob));
        done += 1;
        onProgress?.(done, steps.length);
      })
    );
    this.primed = true;
  }

  private urlOf(g: number): string {
    const { step, local } = stepOfGlobal(g, this.f);
    return frameUrl(step, local, this.opts.variant, this.f);
  }

  private stepRange(step: number): [number, number] {
    const s = this.f.steps[step - 1];
    return [s.globalStart, s.globalStart + s.count - 1];
  }

  /** Re-prioritise around the playhead: current step (outward from the playhead, ahead first), then the next. */
  setPlayhead(global: number, direction: 1 | -1): void {
    this.playhead = Math.round(global);
    this.direction = direction;
    const { step } = stepOfGlobal(this.playhead, this.f);
    const order: number[] = [];
    const [a, b] = this.stepRange(step);
    for (let d = 0; d <= b - a; d++) {
      const ahead = this.playhead + d * direction;
      const behind = this.playhead - d * direction;
      if (ahead >= a && ahead <= b) order.push(ahead);
      if (d && behind >= a && behind <= b) order.push(behind);
    }
    const nextStep = direction > 0 ? step + 1 : step - 1;
    if (nextStep >= 1 && nextStep <= this.f.steps.length) {
      const [na, nb] = this.stepRange(nextStep);
      const seq = [];
      for (let g = na; g <= nb; g++) seq.push(g);
      order.push(...(direction > 0 ? seq : seq.reverse()));
    }
    this.queue = order.filter((g) => !this.blobs.has(g) && !this.inflight.has(g));
    this.evict(step);
    this.pump();
    this.decodeWindow();
  }

  private pump(): void {
    const max = this.opts.maxConcurrent ?? 6;
    while (!this.disposed && this.active < max && this.queue.length) {
      const g = this.queue.shift() as number;
      if (this.blobs.has(g) || this.inflight.has(g)) continue;
      this.active += 1;
      const p = this.fetchBlob(this.urlOf(g))
        .then((blob) => {
          if (this.disposed) return;
          this.blobs.set(g, blob);
          if (Math.abs(g - this.playhead) <= this.opts.decodeWindow) this.decodeOne(g);
        })
        .catch(() => undefined)
        .finally(() => {
          this.active -= 1;
          this.inflight.delete(g);
          this.pump();
        });
      this.inflight.set(g, p);
    }
  }

  private decodeOne(g: number): void {
    if (this.bitmaps.has(g) || this.decoding.has(g)) return;
    const blob = this.blobs.get(g);
    if (!blob) return;
    this.decoding.add(g);
    this.decodeFrame(blob)
      .then((bmp) => {
        this.decoding.delete(g);
        if (this.disposed || Math.abs(g - this.playhead) > this.opts.decodeWindow * 2) {
          bmp.close();
          return;
        }
        this.bitmaps.set(g, bmp);
        this.opts.onReady?.(g);
      })
      .catch(() => this.decoding.delete(g));
  }

  private decodeWindow(): void {
    const w = this.opts.decodeWindow;
    const ahead = Math.round(w * 1.5);
    const behind = Math.round(w * 0.5);
    for (let d = 0; d <= ahead; d++) this.decodeOne(this.playhead + d * this.direction);
    for (let d = 1; d <= behind; d++) this.decodeOne(this.playhead - d * this.direction);
    for (const [g, bmp] of this.bitmaps) {
      if (Math.abs(g - this.playhead) > w * 2) {
        bmp.close();
        this.bitmaps.delete(g);
      }
    }
  }

  /** Drop compressed frames of steps more than 2 away from the active step (SPEC §5.2). */
  evict(activeStep: number): void {
    for (const g of [...this.blobs.keys()]) {
      if (Math.abs(stepOfGlobal(g, this.f).step - activeStep) > 2) this.blobs.delete(g);
    }
  }

  get(global: number): ImageBitmap | null {
    return this.bitmaps.get(Math.round(global)) ?? null;
  }

  /** Nearest decoded frame → this step's placeholder → any placeholder. Never null once placeholders are loaded. */
  nearest(global: number): ImageBitmap | null {
    const g = Math.round(global);
    const exact = this.bitmaps.get(g);
    if (exact) return exact;
    let best: ImageBitmap | null = null;
    let bestD = Infinity;
    for (const [k, bmp] of this.bitmaps) {
      const d = Math.abs(k - g);
      if (d < bestD) {
        bestD = d;
        best = bmp;
      }
    }
    const { step } = stepOfGlobal(g, this.f);
    if (best && bestD <= 24) {
      this.counters.fallbacks += 1;
      return best;
    }
    const ph = this.placeholders.get(step) ?? [...this.placeholders.values()][0] ?? best;
    if (ph) this.counters.fallbacks += 1;
    else if (this.primed) this.counters.blankDraws += 1;
    return ph ?? null;
  }

  hasPlaceholders(): boolean {
    return this.placeholders.size === this.f.steps.length;
  }

  stats(): CacheStats {
    return { blobs: this.blobs.size, bitmaps: this.bitmaps.size, fallbacks: this.counters.fallbacks,
      blankDraws: this.counters.blankDraws, frame: this.playhead };
  }

  dispose(): void {
    this.disposed = true;
    for (const b of this.bitmaps.values()) b.close();
    for (const b of this.placeholders.values()) b.close();
    this.bitmaps.clear();
    this.placeholders.clear();
    this.blobs.clear();
    this.queue = [];
  }
}

/** Decode-window size from device memory (Chrome exposes navigator.deviceMemory in GB). */
export function decodeWindowFor(deviceMemoryGb: number | undefined, mobile: boolean): number {
  // phones decode full-HD frames for the portrait band (≈8.5 MB each): 8 frames keeps bitmaps under ~70 MB
  if (deviceMemoryGb !== undefined && deviceMemoryGb <= 4) return 6;
  return mobile ? 8 : 16;
}
