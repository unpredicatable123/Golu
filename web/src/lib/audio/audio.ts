// Audio layer (SPEC §5.4): Howler for recorded files, Web Audio synthesis when files are missing.
import type { Howl as HowlT } from 'howler';
import type { GoluConfig } from '../config';
import { frames } from '../frames';
import { synthBell, synthOmDrone } from './synth';

const STORE_KEY = 'golu-audio';

function readPersisted(): { muted: boolean; volume: number } {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const v = JSON.parse(raw);
      return { muted: !!v.muted, volume: typeof v.volume === 'number' ? Math.min(1, Math.max(0, v.volume)) : 1 };
    }
  } catch {
    /* storage unavailable (private mode, blocked) — defaults below */
  }
  return { muted: false, volume: 1 };
}

function writePersisted(state: { muted: boolean; volume: number }): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

type Cue = 'om' | 'bellLarge' | 'bellSmall' | 'nadaswaram';

export class AudioManager {
  private howls: Partial<Record<Cue, HowlT>> = {};
  private missing = new Set<Cue>();
  private omId: number | null = null;
  private omSrc: string[] | null = null;
  private HowlCtor: typeof HowlT | null = null;
  private omSynth: { stop(): void } | null = null;
  private omSynthGain: GainNode | null = null;
  private ctx: AudioContext | null = null;
  private out: GainNode | null = null;
  private ambientTimer: ReturnType<typeof setTimeout> | null = null;
  private lastNada = new Map<number, number>();
  private ducked = false;
  muted: boolean;
  volume: number;

  constructor(private cfg: GoluConfig['audio']) {
    const p = readPersisted();
    this.muted = p.muted;
    this.volume = p.volume;
  }

  /** Load the recorded cues; any that fail are synthesised instead. Returns the missing file stems. */
  async load(): Promise<{ missing: string[] }> {
    const { Howl, Howler } = await import('howler');
    this.HowlCtor = Howl;
    Howler.autoUnlock = true;
    const files: Record<Cue, { file: string; loop?: boolean }> = {
      om: { file: this.cfg.om_loop.file, loop: true },
      bellLarge: { file: this.cfg.bell_large.file },
      bellSmall: { file: this.cfg.bell_small.file },
      nadaswaram: { file: this.cfg.nadaswaram_short.file },
    };
    const present = new Set(frames.audio ?? []);
    await Promise.all(
      (Object.keys(files) as Cue[]).map(
        (cue) =>
          new Promise<void>((resolve) => {
            const src = this.cfg.formats
              .filter((ext) => present.has(`${files[cue].file}.${ext}`))
              .map((ext) => `/audio/${files[cue].file}.${ext}?v=${frames.version}`);
            if (!src.length) {
              this.missing.add(cue);
              resolve();
              return;
            }
            if (cue === 'om') {
              // the Om recording is minutes long: stream it after Enter instead of downloading it up front
              // (keeps the pre-Enter payload under budget); startOm() creates the streaming Howl
              this.omSrc = src;
              resolve();
              return;
            }
            const h = new Howl({
              src,
              format: src.map((u) => u.split('?')[0].split('.').pop() as string),
              loop: !!files[cue].loop,
              preload: true,
              html5: false,
              onload: () => resolve(),
              onloaderror: () => {
                this.missing.add(cue);
                resolve();
              },
            });
            this.howls[cue] = h;
          })
      )
    );
    if (this.missing.size) console.info('[golu] audio files missing, using synthesis:', [...this.missing]);
    return { missing: [...this.missing].map((c) => files[c].file) };
  }

  /** Must run inside the Enter click handler (autoplay policy). */
  async unlock(): Promise<void> {
    const { Howler } = await import('howler');
    this.ctx = Howler.ctx ?? new AudioContext();
    if (this.ctx.state !== 'running') await this.ctx.resume();
    this.out = this.ctx.createGain();
    this.out.gain.value = this.muted ? 0 : this.volume;
    this.out.connect(this.ctx.destination);
    Howler.volume(this.muted ? 0 : this.volume);
  }

  state(): { state: string; om: number; missing: string[] } {
    const om = this.howls.om && this.omId !== null
      ? (this.howls.om.volume(this.omId) as number)
      : this.omSynthGain ? this.omSynthGain.gain.value : 0;
    return { state: this.ctx?.state ?? 'none', om, missing: [...this.missing] };
  }

  private play(cue: Cue, volume: number, rate = 1): void {
    const h = this.howls[cue];
    if (h && !this.missing.has(cue)) {
      const id = h.play();
      h.volume(volume, id);
      h.rate(rate, id);
      return;
    }
    if (!this.ctx || !this.out) return;
    if (cue === 'bellLarge') synthBell(this.ctx, this.out, 'large', volume);
    else if (cue === 'bellSmall') synthBell(this.ctx, this.out, 'small', volume);
  }

  bellLarge(): void {
    this.play('bellLarge', this.cfg.bell_large.volume);
  }

  bellSmall(volume = this.cfg.bell_small.volume): void {
    this.play('bellSmall', volume, 0.97 + Math.random() * 0.06);
  }

  /** Om loop fades in to its configured level (0.35) over 3 s (SPEC §5.1). */
  startOm(): void {
    const target = this.cfg.om_loop.volume;
    const fade = this.cfg.om_loop.fade_in_seconds * 1000;
    if (this.omSrc && this.HowlCtor && !this.howls.om) {
      const h = new this.HowlCtor({
        src: this.omSrc,
        format: this.omSrc.map((u) => u.split('?')[0].split('.').pop() as string),
        html5: true,          // stream: playback starts before the whole file has downloaded
        loop: true,
        volume: 0,
        onloaderror: () => this.omFallback(),
        onplayerror: () => this.omFallback(),
      });
      this.howls.om = h;
      this.omId = h.play();
      h.fade(0, this.ducked ? this.cfg.om_loop.ducked_volume : target, fade, this.omId);
      return;
    }
    this.startOmSynth();
  }

  /** The recording failed to stream: fall back to the synthesised drone. */
  private omFallback(): void {
    if (this.omSynth) return;
    console.info('[golu] Om recording unavailable, using synthesis');
    this.howls.om?.unload();
    this.howls.om = undefined;
    this.omId = null;
    this.missing.add('om');
    this.startOmSynth();
  }

  private startOmSynth(): void {
    const target = this.cfg.om_loop.volume;
    const fade = this.cfg.om_loop.fade_in_seconds * 1000;
    if (!this.ctx || !this.out) return;
    const g = this.ctx.createGain();
    g.gain.value = 0;
    g.connect(this.out);
    g.gain.linearRampToValueAtTime(target, this.ctx.currentTime + fade / 1000);
    this.omSynthGain = g;
    this.omSynth = synthOmDrone(this.ctx, g, this.cfg.fallback.om_fundamental_hz, this.cfg.fallback.om_swell_seconds);
  }

  /** 0.35 ↔ 0.20 during rituals. */
  duck(on: boolean): void {
    if (on === this.ducked) return;
    this.ducked = on;
    const to = on ? this.cfg.om_loop.ducked_volume : this.cfg.om_loop.volume;
    const h = this.howls.om;
    if (h && this.omId !== null) h.fade(h.volume(this.omId) as number, to, 600, this.omId);
    if (this.omSynthGain && this.ctx) this.omSynthGain.gain.setTargetAtTime(to, this.ctx.currentTime, 0.2);
  }

  /** Soft nadaswaram on entering the wedding steps, once per visit (DECISIONS D42). */
  nadaswaram(step: number, previousStep: number): void {
    if (!this.cfg.nadaswaram_short.steps.includes(step) || this.missing.has('nadaswaram')) return;
    const now = performance.now();
    const last = this.lastNada.get(step) ?? -Infinity;
    if (previousStep === step || now - last < 10_000) return;
    this.lastNada.set(step, now);
    this.play('nadaswaram', this.cfg.nadaswaram_short.volume);
  }

  /** Occasional soft bell every 20–40 s (random). */
  startAmbientBells(isBusy: () => boolean): void {
    const { ambient_min_seconds: lo, ambient_max_seconds: hi, ambient_volume: v } = this.cfg.bell_small;
    const next = () => {
      this.ambientTimer = setTimeout(() => {
        if (!isBusy() && !document.hidden) this.bellSmall(v);
        next();
      }, (lo + Math.random() * (hi - lo)) * 1000);
    };
    this.stopAmbientBells();
    next();
  }

  stopAmbientBells(): void {
    if (this.ambientTimer) clearTimeout(this.ambientTimer);
    this.ambientTimer = null;
  }

  async setMuted(m: boolean): Promise<void> {
    this.muted = m;
    const { Howler } = await import('howler');
    Howler.volume(m ? 0 : this.volume);
    if (this.out && this.ctx) this.out.gain.setTargetAtTime(m ? 0 : this.volume, this.ctx.currentTime, 0.05);
    writePersisted({ muted: this.muted, volume: this.volume });
  }

  async setVolume(v: number): Promise<void> {
    this.volume = Math.min(1, Math.max(0, v));
    const { Howler } = await import('howler');
    if (!this.muted) Howler.volume(this.volume);
    if (this.out && this.ctx && !this.muted) this.out.gain.setTargetAtTime(this.volume, this.ctx.currentTime, 0.05);
    writePersisted({ muted: this.muted, volume: this.volume });
  }
}
