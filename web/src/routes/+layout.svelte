<script lang="ts">
  import '@fontsource/noto-serif-tamil/tamil-400.css';
  import '@fontsource/noto-serif-tamil/tamil-600.css';
  import '@fontsource/cormorant-garamond/latin-500.css';
  import '@fontsource/cormorant-garamond/latin-600.css';
  import '@fontsource/cormorant-garamond/latin-500-italic.css';
  import '../app.css';
  import type { Snippet } from 'svelte';
  import { config, tokenCss } from '$lib/config';

  let { children }: { children: Snippet } = $props();
  const css = tokenCss();
</script>

<svelte:head>
  <title>{config.meta.title_ta} · {config.meta.title_en}</title>
  <meta name="description" content={`${config.meta.description_en} ${config.meta.description_ta}`} />
  <meta property="og:title" content={`${config.meta.title_ta} · ${config.meta.title_en}`} />
  <meta property="og:description" content={config.meta.description_en} />
  <meta property="og:image" content="/props/tray_composite.webp" />
  {@html `<style>${css}</style>`}
</svelte:head>

{@render children()}
