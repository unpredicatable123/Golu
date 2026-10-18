// See https://svelte.dev/docs/kit/types#app.d.ts
declare global {
  namespace App {}
  interface Window {
    /** Debug/test hooks (dev and test builds); used by Playwright to assert "never blank" and ritual turns. */
    __golu?: {
      stats: () => { blobs: number; bitmaps: number; fallbacks: number; blankDraws: number; frame: number };
      ritualLog: Array<{ kind: string; cwTurns: number; ccwTurns: number }>;
      audio: () => { state: string; om: number; missing: string[] };
    };
  }
}

export {};
