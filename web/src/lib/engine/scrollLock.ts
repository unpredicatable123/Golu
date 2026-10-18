// Scroll is paused during a ritual and restored afterwards (SPEC §5.3).
const KEYS = new Set(['ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End', ' ', 'Spacebar']);

export function lockScroll(): () => void {
  const y = window.scrollY;
  const html = document.documentElement;
  const prev = { overflow: html.style.overflow, touch: html.style.touchAction, body: document.body.style.overflow };
  html.style.overflow = 'hidden';
  html.style.touchAction = 'none';
  document.body.style.overflow = 'hidden';
  const block = (e: Event) => e.preventDefault();
  const keys = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement | null;
    const typing = target && (target.tagName === 'INPUT' || target.tagName === 'BUTTON' || target.isContentEditable);
    if (KEYS.has(e.key) && !(typing && e.key === ' ')) e.preventDefault();
  };
  window.addEventListener('wheel', block, { passive: false });
  window.addEventListener('touchmove', block, { passive: false });
  window.addEventListener('keydown', keys);
  return () => {
    window.removeEventListener('wheel', block);
    window.removeEventListener('touchmove', block);
    window.removeEventListener('keydown', keys);
    html.style.overflow = prev.overflow;
    html.style.touchAction = prev.touch;
    document.body.style.overflow = prev.body;
    window.scrollTo(0, y);
  };
}
