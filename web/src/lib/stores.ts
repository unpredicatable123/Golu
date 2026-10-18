import { readable, writable } from 'svelte/store';

export type RitualKind = 'aarthi' | 'camphor' | 'prasadam';

export const entered = writable(false);
export const activeStep = writable(1);
export const globalFrame = writable(0);
export const ritual = writable<RitualKind | null>(null);
export const openDoll = writable<string | null>(null);

/** prefers-reduced-motion as a live store (SPEC §5.5). */
export const reducedMotion = readable(false, (set) => {
  if (typeof window === 'undefined' || !window.matchMedia) return;
  const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
  set(mq.matches);
  const on = (e: MediaQueryListEvent) => set(e.matches);
  mq.addEventListener('change', on);
  return () => mq.removeEventListener('change', on);
});
