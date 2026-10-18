// Live canvas flame for the aarthi / camphor plates (SPEC §5.3): teardrop core, orange-yellow gradient,
// flicker noise, additive glow. Camphor burns brighter, whiter and taller, and can be extinguished.

export type FlameKind = 'ghee' | 'camphor';

/** Smooth 1-D value noise (deterministic per seed), octaves summed. */
export function makeNoise(seed: number): (x: number) => number {
  const table = new Float32Array(256);
  let s = seed >>> 0 || 1;
  for (let i = 0; i < 256; i++) {
    s = (s * 1664525 + 1013904223) >>> 0;
    table[i] = s / 0xffffffff;
  }
  const v = (x: number) => {
    const i = Math.floor(x);
    const f = x - i;
    const a = table[i & 255];
    const b = table[(i + 1) & 255];
    const u = f * f * (3 - 2 * f);
    return a + (b - a) * u;
  };
  return (x: number) => (v(x) * 0.6 + v(x * 2.3 + 17) * 0.28 + v(x * 5.1 + 41) * 0.12) * 2 - 1;
}

const PALETTE: Record<FlameKind, { core: string; mid: string; outer: string; glow: string; height: number; width: number }> = {
  ghee: { core: '#FFF2C8', mid: '#FFC64A', outer: '#FF7A1A', glow: 'rgba(255,150,40,', height: 1, width: 1 },
  camphor: { core: '#FFFFFF', mid: '#FFF0B0', outer: '#FFB840', glow: 'rgba(255,215,140,', height: 1.5, width: 0.9 },
};

export class FlameRenderer {
  private t = 0;
  private x = 0;
  private y = 0;
  private scale = 1;
  private life = 1;          // 1 burning → 0 out
  private frozen = false;
  private noiseH: (x: number) => number;
  private noiseL: (x: number) => number;
  private noiseB: (x: number) => number;

  constructor(private ctx: CanvasRenderingContext2D, private kind: FlameKind, seed = 7) {
    this.noiseH = makeNoise(seed);
    this.noiseL = makeNoise(seed * 3 + 1);
    this.noiseB = makeNoise(seed * 7 + 2);
  }

  /** Wick tip in canvas pixels; size scales the flame (1 ≈ 46 px tall ghee flame). */
  setAnchor(x: number, y: number, size = 1): void {
    this.x = x;
    this.y = y;
    this.scale = size;
  }

  /** Reduced motion: hold one steady frame. */
  freeze(): void {
    this.frozen = true;
  }

  get alive(): boolean {
    return this.life > 0.01;
  }

  /** Brightness 0..1 for the light-spill glow (flickers with the flame). */
  intensity(): number {
    return this.life * (0.85 + 0.15 * this.noiseB(this.t * 6));
  }

  step(dt: number): void {
    if (!this.frozen) this.t += dt;
  }

  extinguish(seconds: number): Promise<void> {
    const start = performance.now();
    return new Promise((resolve) => {
      const tick = () => {
        const k = (performance.now() - start) / (seconds * 1000);
        this.life = Math.max(0, 1 - k * k);
        if (k < 1) requestAnimationFrame(tick);
        else {
          this.life = 0;
          resolve();
        }
      };
      requestAnimationFrame(tick);
    });
  }

  draw(): void {
    if (!this.alive) return;
    const c = this.ctx;
    const p = PALETTE[this.kind];
    const t = this.t;
    const h = 46 * this.scale * p.height * this.life * (0.88 + 0.14 * this.noiseH(t * 7) + 0.05 * this.noiseH(t * 19));
    const w = 15 * this.scale * p.width * (0.7 + 0.3 * this.life) * (0.94 + 0.06 * this.noiseB(t * 5));
    const lean = 0.18 * this.noiseL(t * 3.2) * h;
    const x = this.x;
    const y = this.y;
    c.save();
    c.globalCompositeOperation = 'lighter';
    // soft halo
    const halo = c.createRadialGradient(x, y - h * 0.45, 0, x, y - h * 0.45, h * 1.6);
    halo.addColorStop(0, `${p.glow}${0.42 * this.intensity()})`);
    halo.addColorStop(1, `${p.glow}0)`);
    c.fillStyle = halo;
    c.beginPath();
    c.arc(x, y - h * 0.45, h * 1.6, 0, Math.PI * 2);
    c.fill();
    // teardrop body: two Béziers from the wick to the leaning tip
    const tipX = x + lean;
    const tipY = y - h;
    const body = () => {
      c.beginPath();
      c.moveTo(x, y + w * 0.15);
      c.bezierCurveTo(x - w, y - h * 0.08, x - w * 0.55 + lean * 0.5, y - h * 0.62, tipX, tipY);
      c.bezierCurveTo(x + w * 0.55 + lean * 0.5, y - h * 0.62, x + w, y - h * 0.08, x, y + w * 0.15);
      c.closePath();
    };
    const grad = c.createLinearGradient(x, y, tipX, tipY);
    grad.addColorStop(0, this.kind === 'ghee' ? 'rgba(90,120,255,0.55)' : 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.12, p.core);
    grad.addColorStop(0.45, p.mid);
    grad.addColorStop(0.85, p.outer);
    grad.addColorStop(1, 'rgba(255,90,10,0)');
    c.globalAlpha = 0.9 * this.life;
    c.fillStyle = grad;
    body();
    c.fill();
    // hot inner core
    c.globalAlpha = 0.85 * this.life;
    const core = c.createRadialGradient(x, y - h * 0.22, 0, x, y - h * 0.22, w * 0.8);
    core.addColorStop(0, p.core);
    core.addColorStop(1, 'rgba(255,240,200,0)');
    c.fillStyle = core;
    c.beginPath();
    c.ellipse(x + lean * 0.15, y - h * 0.25, w * 0.42, h * 0.3, 0, 0, Math.PI * 2);
    c.fill();
    c.restore();
  }
}
