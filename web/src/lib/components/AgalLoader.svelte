<script lang="ts">
  // Agal-vilakku loading indicator: inline SVG clay lamp with a CSS flame (DECISIONS D43).
  let { progress = 0, ta, en }: { progress?: number; ta: string; en: string } = $props();
  const pct = $derived(Math.round(Math.min(1, Math.max(0, progress)) * 100));
</script>

<div class="loader" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={pct} aria-label={`${ta} — ${en}`}>
  <svg viewBox="0 0 120 90" width="96" height="72" aria-hidden="true">
    <defs>
      <radialGradient id="agal-glow" cx="50%" cy="40%" r="60%">
        <stop offset="0%" stop-color="#ffcf6a" stop-opacity="0.55" />
        <stop offset="100%" stop-color="#ff8a1a" stop-opacity="0" />
      </radialGradient>
      <linearGradient id="agal-clay" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="#c46a3a" />
        <stop offset="100%" stop-color="#6e2d12" />
      </linearGradient>
      <linearGradient id="agal-flame" x1="0" x2="0" y1="1" y2="0">
        <stop offset="0%" stop-color="#ff7a1a" />
        <stop offset="45%" stop-color="#ffc64a" />
        <stop offset="100%" stop-color="#fff2c8" />
      </linearGradient>
    </defs>
    <circle cx="60" cy="30" r="34" fill="url(#agal-glow)" class="glow" />
    <path class="flame" d="M60 6 C53 18 52 26 56 33 C58 36 62 36 64 33 C68 26 67 18 60 6 Z" fill="url(#agal-flame)" />
    <path d="M18 52 C30 72 90 72 102 52 C92 58 28 58 18 52 Z M96 50 L112 44 L104 54 Z" fill="url(#agal-clay)" />
    <ellipse cx="60" cy="52" rx="42" ry="6" fill="#4a1d0b" />
    <ellipse cx="60" cy="50" rx="40" ry="4" fill="#d9a441" opacity="0.6" />
  </svg>
  <div class="label">
    <span class="ta" lang="ta">{ta}</span>
    <span class="en" lang="en">{en} {pct}%</span>
  </div>
</div>

<style>
  .loader {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.4rem;
    color: var(--tok-sandal);
  }
  .flame {
    transform-origin: 60px 34px;
    animation: flicker 1.3s infinite ease-in-out alternate;
  }
  .glow {
    animation: breathe 2.2s infinite ease-in-out alternate;
  }
  @keyframes flicker {
    0% { transform: scale(1, 1) skewX(0deg); }
    30% { transform: scale(0.94, 1.06) skewX(2deg); }
    60% { transform: scale(1.03, 0.95) skewX(-2deg); }
    100% { transform: scale(0.97, 1.04) skewX(1deg); }
  }
  @keyframes breathe {
    from { opacity: 0.7; }
    to { opacity: 1; }
  }
  .label {
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 0.9rem;
  }
  .en { opacity: 0.8; letter-spacing: 0.05em; }
</style>
