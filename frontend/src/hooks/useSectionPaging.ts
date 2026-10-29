import { useEffect } from 'react';
import { scrollToSection } from '../utils/scroll';

export function useSectionPaging(ids: readonly string[]) {
  useEffect(() => {
    let locked = false;
    let accumulated = 0;
    let unlockTimer: number | undefined;

    const unlock = () => {
      locked = false;
      accumulated = 0;
    };

    // Scroll position where each section would land, sorted top to bottom
    const getStops = () => {
      const seen = new Set<Element>();
      const stops: { id: string; y: number }[] = [];
      for (const id of ids) {
        const el = document.getElementById(id);
        if (!el || seen.has(el)) continue;
        seen.add(el);
        const margin = parseFloat(getComputedStyle(el).scrollMarginTop) || 0;
        const y = id === 'home' ? 0 : el.getBoundingClientRect().top + window.scrollY - margin;
        stops.push({ id, y });
      }
      return stops.sort((a, b) => a.y - b.y);
    };

    const onWheel = (event: WheelEvent) => {
      if (
        event.ctrlKey ||
        Math.abs(event.deltaY) < 2 ||
        (event.target instanceof Element &&
          event.target.closest(
            'input, textarea, select, [contenteditable="true"], [data-native-scroll]',
          ))
      ) {
        return;
      }

      if (locked) {
        event.preventDefault();
        return;
      }

      const direction = Math.sign(event.deltaY);
      const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
      const y = window.scrollY;
      const stops = getStops();

      const next =
        direction > 0
          ? stops.find((s) => Math.min(s.y, maxScroll) > y + 8)
          : [...stops].reverse().find((s) => s.y < y - 8);

      // Nothing to page to (top, bottom, or footer): let the browser scroll normally
      if (!next) return;

      accumulated += event.deltaY;
      if (Math.abs(accumulated) < 45) {
        event.preventDefault();
        return;
      }

      event.preventDefault();
      locked = true;
      accumulated = 0;
      scrollToSection(next.id);

      window.clearTimeout(unlockTimer);
      unlockTimer = window.setTimeout(unlock, 850);
    };

    window.addEventListener('wheel', onWheel, { passive: false });

    return () => {
      window.removeEventListener('wheel', onWheel);
      window.clearTimeout(unlockTimer);
    };
  }, [ids]);
}