// Shared mapping from frame space (0..1) to viewport pixels for overlays (hotspots, lamp flicker, rituals).
import { writable } from 'svelte/store';
import type { Rect } from './coverFit';

export interface View { rect: Rect; srcW: number; srcH: number; width: number; height: number; step: number; local: number }

export const view = writable<View | null>(null);
