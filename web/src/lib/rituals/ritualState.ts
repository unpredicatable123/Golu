// Only one ritual at a time; scroll locked and Om ducked while it runs (SPEC §5.3).
import { get } from 'svelte/store';
import type { AudioManager } from '../audio/audio';
import { lockScroll } from '../engine/scrollLock';
import { ritual, type RitualKind } from '../stores';

export function startRitual(kind: RitualKind, audio: AudioManager | null): (() => void) | null {
  if (get(ritual) !== null) return null;
  ritual.set(kind);
  const unlock = lockScroll();
  audio?.duck(true);
  let done = false;
  return () => {
    if (done) return;
    done = true;
    unlock();
    audio?.duck(false);
    ritual.set(null);
  };
}

export function logRitual(kind: string, cwTurns: number, ccwTurns: number): void {
  if (typeof window === 'undefined') return;
  const w = window as Window;
  if (!w.__golu) return;
  w.__golu.ritualLog.push({ kind, cwTurns, ccwTurns });
}
