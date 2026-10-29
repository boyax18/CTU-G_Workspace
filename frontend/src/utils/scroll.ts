const behavior = (): ScrollBehavior =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';

export function scrollToSection(id: string): void {
  if (id === 'home') {
    window.scrollTo({ top: 0, behavior: behavior() });
    return;
  }
  const el = document.getElementById(id);
  if (!el) return;
  const offset = parseFloat(getComputedStyle(el).scrollMarginTop) || 0; // keeps the section clear of the sticky navbar
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - offset, behavior: behavior() });
}

/** The login card lives in the hero, so go there and focus the first field. */
export function focusLoginForm(): void {
  scrollToSection('home');
  window.setTimeout(() => {
    document.getElementById('school-id')?.focus({ preventScroll: true });
  }, 600);
}
