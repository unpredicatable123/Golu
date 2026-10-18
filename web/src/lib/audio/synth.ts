// Web Audio fallbacks used when the recorded audio files are missing (SPEC §5.4).

/** Temple bell: inharmonic partials (hum, prime, tierce, quint, nominal…) with exponential decays. */
export function synthBell(ctx: AudioContext, out: AudioNode, kind: 'large' | 'small', volume = 1): void {
  const base = kind === 'large' ? 196 : 880;
  const decay = kind === 'large' ? 2.2 : 1.0;
  const ratios = [0.5, 1, 1.19, 1.56, 2.0, 2.51, 2.66, 3.01, 4.17];
  const t0 = ctx.currentTime + 0.005;
  const master = ctx.createGain();
  master.gain.value = volume * (kind === 'large' ? 0.5 : 0.32);
  master.connect(out);
  ratios.forEach((r, k) => {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.value = base * r * (1 + (k % 2 ? 0.0012 : -0.0009));    // slight detune → bell beating
    const amp = 1 / Math.pow(k + 1, 0.7);
    const len = (decay * (6 - Math.min(k, 5) * 0.8)) / (k < 2 ? 1 : 1.4);
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(amp, t0 + 0.004);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + Math.max(0.4, len));
    osc.connect(g).connect(master);
    osc.start(t0);
    osc.stop(t0 + Math.max(0.4, len) + 0.05);
  });
}

/** Om drone: tanpura-like 136.1 Hz fundamental with harmonics, slow swell, soft "jawari" buzz, low-passed. */
export function synthOmDrone(ctx: AudioContext, out: AudioNode, fundamental = 136.1, swellSeconds = 9): { stop(): void } {
  const master = ctx.createGain();
  master.gain.value = 0;
  const lp = ctx.createBiquadFilter();
  lp.type = 'lowpass';
  lp.frequency.value = 1800;
  const shaper = ctx.createWaveShaper();
  const curve = new Float32Array(1024);
  for (let i = 0; i < curve.length; i++) {
    const x = (i / (curve.length - 1)) * 2 - 1;
    curve[i] = Math.tanh(2.2 * x) * 0.85;
  }
  shaper.curve = curve;
  shaper.connect(lp).connect(master).connect(out);
  const weights = [1, 0.55, 0.38, 0.3, 0.18, 0.12];
  const oscs: OscillatorNode[] = [];
  weights.forEach((w, k) => {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.type = k === 0 ? 'triangle' : 'sine';
    o.frequency.value = fundamental * (k + 1) * (1 + (k % 2 ? 0.0006 : -0.0004));
    g.gain.value = w * 0.22;
    o.connect(g).connect(shaper);
    o.start();
    oscs.push(o);
  });
  // slow swell (LFO on the master gain around a base level)
  const lfo = ctx.createOscillator();
  const lfoGain = ctx.createGain();
  lfo.frequency.value = 1 / Math.max(2, swellSeconds);
  lfoGain.gain.value = 0.25;
  const base = ctx.createConstantSource();
  base.offset.value = 0.75;
  lfo.connect(lfoGain).connect(master.gain);
  base.connect(master.gain);
  lfo.start();
  base.start();
  return {
    stop() {
      const t = ctx.currentTime;
      master.gain.cancelScheduledValues(t);
      master.gain.setTargetAtTime(0, t, 0.3);
      for (const o of [...oscs, lfo]) o.stop(t + 1.5);
      base.stop(t + 1.5);
    },
  };
}
