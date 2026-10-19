import type { Handle } from '@sveltejs/kit';

// Preload the web fonts from the prerendered <head> (SvelteKit preloads only JS and CSS by default): the
// entrance title is the largest contentful paint, and on slow mobile networks it waited for the Tamil font.
export const handle: Handle = ({ event, resolve }) =>
  resolve(event, {
    preload: ({ type, path }) => type === 'js' || type === 'css' || (type === 'font' && path.endsWith('.woff2')),
  });
