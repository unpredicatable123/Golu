// Small canvas particle systems for the rituals: camphor smoke (curl drift), prasadam steam, flower petals,
// and the warm light-spill glow (SPEC §5.3).
import { makeNoise } from './flame';

interface Wisp { x: number; y: number; age: number; life: number; w: number; seed: number }

/** Thin rising smoke wisps that curl as they drift (2-D curl of a noise field). */
export class SmokeWisps {
  private wisps: Wisp[] = [];
  private n1 = makeNoise(11);
  private n2 = makeNoise(29);

  constructor(private ctx: CanvasRenderingContext2D) {}

  emit(x: number, y: number, count = 1, life = 2.6): void {
    for (let i = 0; i < count; i++) {
      this.wisps.push({ x: x + (Math.random() - 0.5) * 4, y, age: 0, life: life * (0.8 + Math.random() * 0.4),
        w: 1 + Math.random() * 1.5, seed: Math.random() * 100 });
    }
  }

  get active(): boolean {
    return this.wisps.length > 0;
  }

  step(dt: number): void {
    for (const p of this.wisps) {
      p.age += dt;
      const k = p.seed + p.age * 0.9;
      const curlX = this.n1(k) * 22 + this.n2(k * 1.7) * 9;
      p.x += curlX * dt;
      p.y -= (34 + 18 * this.n2(k)) * dt;
    }
    this.wisps = this.wisps.filter((p) => p.age < p.life);
  }

  draw(): void {
    const c = this.ctx;
    c.save();
    c.lineCap = 'round';
    for (const p of this.wisps) {
      const a = Math.sin(Math.PI * Math.min(1, p.age / p.life)) * 0.35;
      c.strokeStyle = `rgba(235,225,215,${a})`;
      c.lineWidth = p.w + p.age * 2.2;
      c.beginPath();
      const len = 14 + p.age * 10;
      c.moveTo(p.x, p.y);
      c.quadraticCurveTo(p.x + this.n1(p.seed + p.age) * 10, p.y + len * 0.5, p.x - this.n2(p.seed) * 6, p.y + len);
      c.stroke();
    }
    c.restore();
  }
}

/** Soft steam curls above the prasadam bowls. */
export class Steam {
  private puffs: Array<{ x: number; y: number; age: number; life: number; r: number; seed: number }> = [];
  private n = makeNoise(5);
  private acc = 0;

  constructor(private ctx: CanvasRenderingContext2D, private sources: () => Array<[number, number]>) {}

  step(dt: number): void {
    this.acc += dt;
    while (this.acc > 0.12) {
      this.acc -= 0.12;
      for (const [x, y] of this.sources()) {
        this.puffs.push({ x: x + (Math.random() - 0.5) * 30, y, age: 0, life: 2.4 + Math.random(), r: 6 + Math.random() * 6,
          seed: Math.random() * 50 });
      }
    }
    for (const p of this.puffs) {
      p.age += dt;
      p.x += this.n(p.seed + p.age) * 12 * dt;
      p.y -= 22 * dt;
      p.r += 7 * dt;
    }
    this.puffs = this.puffs.filter((p) => p.age < p.life);
  }

  draw(): void {
    const c = this.ctx;
    c.save();
    for (const p of this.puffs) {
      const a = Math.sin(Math.PI * (p.age / p.life)) * 0.12;
      const g = c.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r);
      g.addColorStop(0, `rgba(255,248,235,${a})`);
      g.addColorStop(1, 'rgba(255,248,235,0)');
      c.fillStyle = g;
      c.beginPath();
      c.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      c.fill();
    }
    c.restore();
  }
}

interface Petal { x: number; y: number; vx: number; vy: number; rot: number; vr: number; sway: number; img: number; s: number }

/** Falling flower-petal shower (pushpa vrishti) using rendered petal sprites. */
export class PetalShower {
  private petals: Petal[] = [];
  private t = 0;

  constructor(private ctx: CanvasRenderingContext2D, private sprites: HTMLImageElement[]) {}

  start(width: number, count: number): void {
    this.t = 0;
    this.petals = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: -40 - Math.random() * 600,
      vx: (Math.random() - 0.5) * 20,
      vy: 60 + Math.random() * 70,
      rot: Math.random() * Math.PI * 2,
      vr: (Math.random() - 0.5) * 3,
      sway: Math.random() * Math.PI * 2,
      img: Math.floor(Math.random() * Math.max(1, this.sprites.length)),
      s: 0.12 + Math.random() * 0.12,
    }));
  }

  get active(): boolean {
    return this.petals.length > 0;
  }

  step(dt: number, height: number): void {
    this.t += dt;
    for (const p of this.petals) {
      p.x += (p.vx + Math.sin(this.t * 1.6 + p.sway) * 30) * dt;
      p.y += p.vy * dt;
      p.rot += p.vr * dt;
    }
    this.petals = this.petals.filter((p) => p.y < height + 60);
  }

  draw(): void {
    const c = this.ctx;
    for (const p of this.petals) {
      const img = this.sprites[p.img];
      if (!img || !img.complete) continue;
      const w = img.naturalWidth * p.s;
      const h = img.naturalHeight * p.s;
      c.save();
      c.translate(p.x, p.y);
      c.rotate(p.rot);
      c.drawImage(img, -w / 2, -h / 2, w, h);
      c.restore();
    }
  }
}

/** Warm radial light-spill drawn on an overlay canvas with CSS mix-blend-mode: screen. */
export function drawGlow(ctx: CanvasRenderingContext2D, x: number, y: number, radius: number, color: string,
                         intensity: number): void {
  const g = ctx.createRadialGradient(x, y, 0, x, y, radius);
  const rgb = hexToRgb(color);
  g.addColorStop(0, `rgba(${rgb},${0.6 * intensity})`);
  g.addColorStop(0.35, `rgba(${rgb},${0.28 * intensity})`);
  g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
}

function hexToRgb(hex: string): string {
  const h = hex.replace('#', '');
  return `${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)}`;
}
