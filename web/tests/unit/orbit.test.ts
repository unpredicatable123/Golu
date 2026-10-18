import { describe, expect, it } from 'vitest';
import { countTurns, ellipsePoint, orbitAngle, orbitDuration, orbitTravel, type OrbitSpec } from '../../src/lib/rituals/orbit';

const S: OrbitSpec = { cw: 3, ccw: 3, secPerCircle: 1.8, reversalEase: 0.25, startDeg: 90 };

describe('aarthi orbit (SPEC §5.3: exactly 3 clockwise + 3 anticlockwise circles)', () => {
  const dt = 0.001;
  const dur = orbitDuration(S);
  const samples: number[] = [];
  const n = Math.round(dur / dt);
  for (let i = 0; i <= n; i++) samples.push(orbitTravel((i / n) * dur, S));

  it('peaks at exactly +1080° and returns to 0°', () => {
    expect(Math.max(...samples)).toBeCloseTo(1080, 1);
    expect(samples[samples.length - 1]).toBeCloseTo(0, 1);
  });

  it('changes direction exactly once', () => {
    let changes = 0;
    let prevSign = 0;
    for (let i = 1; i < samples.length; i++) {
      const d = samples[i] - samples[i - 1];
      const sign = Math.abs(d) < 1e-9 ? 0 : Math.sign(d);
      if (sign && prevSign && sign !== prevSign) changes++;
      if (sign) prevSign = sign;
    }
    expect(changes).toBe(1);
  });

  it('counts 3 + 3 turns', () => {
    expect(countTurns(samples)).toEqual({ cwTurns: 3, ccwTurns: 3 });
  });

  it('runs at one circle per 1.8 s away from the reversal, eased to rest at it', () => {
    const v = (t: number) => (orbitTravel(t + 0.01, S) - orbitTravel(t - 0.01, S)) / 0.02;
    expect(v(1.0)).toBeCloseTo(360 / 1.8, 0);
    const reversal = dur / 2;
    expect(Math.abs(v(reversal - 0.006))).toBeLessThan(20);
    expect(dur).toBeGreaterThan(10.8);
    expect(dur).toBeLessThan(11.6);
  });

  it('starts at the bottom of the ellipse and moves clockwise on screen (y down)', () => {
    const [x0, y0] = ellipsePoint(orbitAngle(0, S), 0, 0, 100, 50);
    expect(x0).toBeCloseTo(0, 6);
    expect(y0).toBeCloseTo(50, 6);
    const [x1] = ellipsePoint(orbitAngle(0.2, S), 0, 0, 100, 50);
    expect(x1).toBeLessThan(0);    // bottom → left = clockwise when y points down
  });
});
