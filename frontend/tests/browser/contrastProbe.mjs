// Worst-case WCAG contrast for text on translucent, layered dashboard surfaces.
// For each visible text element the probe composites every ancestor background from <html> down:
// background-color, then each background-image layer bottom-up. Gradients contribute every stop
// (each stop is a separate candidate), and an image (url) layer is unknown content, so it is
// replaced by both pure white and pure black. Text colours with alpha are composited too, and
// `extraLayers` (for example a decorative sibling such as the banner ring) can be applied on top.
// The reported ratio is the minimum over all candidates, so it holds at any image crop.

function probe({ selector, extraLayers }) {
  const parse = (value) => {
    const n = value.match(/[\d.]+/g)?.map(Number) ?? [0, 0, 0, 0];
    return [n[0], n[1], n[2], n.length > 3 ? n[3] : 1];
  };
  const over = (top, under) => [0, 1, 2].map((i) => top[3] * top[i] + (1 - top[3]) * under[i]);
  const lum = ([r, g, b]) => {
    const c = [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const extremes = (list) => {
    const sorted = [...list].sort((a, b) => lum(a) - lum(b));
    return sorted.length > 2 ? [sorted[0], sorted.at(-1)] : sorted;
  };
  const layers = (element) => {
    const style = getComputedStyle(element);
    const result = [];
    const color = parse(style.backgroundColor);
    if (color[3] > 0) result.push({ kind: 'color', colors: [color] });
    if (style.backgroundImage && style.backgroundImage !== 'none') {
      // Split top-level layers; CSS lists the top layer first.
      const parts = [];
      let depth = 0; let start = 0;
      const text = style.backgroundImage;
      for (let i = 0; i < text.length; i++) {
        if (text[i] === '(') depth++;
        else if (text[i] === ')') depth--;
        else if (text[i] === ',' && depth === 0) { parts.push(text.slice(start, i)); start = i + 1; }
      }
      parts.push(text.slice(start));
      for (const part of parts.reverse()) {
        if (part.includes('url(')) result.push({ kind: 'image' });
        else if (part.includes('gradient')) {
          const stops = (part.match(/rgba?\([^)]+\)/g) ?? []).map(parse);
          if (stops.length) result.push({ kind: 'color', colors: stops });
        }
      }
    }
    return result;
  };
  const chain = (element) => {
    const nodes = [];
    for (let node = element; node; node = node.parentElement) nodes.unshift(node);
    let candidates = [[255, 255, 255]];
    for (const node of nodes) {
      for (const layer of layers(node)) {
        if (layer.kind === 'image') { candidates = [[255, 255, 255], [0, 0, 0]]; continue; }
        const next = [];
        for (const base of candidates) for (const color of layer.colors) next.push(over(color, base));
        candidates = extremes(next);
      }
    }
    return candidates;
  };
  return [...document.querySelectorAll(selector)]
    .filter((element) => element.getClientRects().length && element.textContent.trim()
      && !element.closest('.sr-only') && getComputedStyle(element).visibility !== 'hidden')
    .map((element) => {
      let backgrounds = chain(element);
      for (const extra of extraLayers.filter((layer) => element.closest(layer.within))) {
        backgrounds = backgrounds.map((base) => over(parse(extra.color), base));
      }
      const fg = parse(getComputedStyle(element).color);
      const ratio = Math.min(...backgrounds.map((bg) => {
        const a = lum(over(fg, bg)); const b = lum(bg);
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      }));
      return { text: element.textContent.trim().replace(/\s+/g, ' ').slice(0, 40), ratio };
    });
}

/** Minimum composited contrast of every visible text node matched by `selector`. */
export function contrastReport(page, selector, extraLayers = []) {
  return page.evaluate(probe, { selector, extraLayers });
}

export const DASHBOARD_TEXT = [
  'header p', 'header span', 'header button',
  '#workspace-sidebar p', '#workspace-sidebar a span', '#workspace-sidebar button span',
  'nav[aria-label="Breadcrumb"] li', 'main h1', 'main h2', 'main h3', 'main p', 'main label', 'main td', 'main th',
  'main dt', 'main dd', 'main button', 'main option', 'main [class*="rounded-full"]',
].join(', ');

/** The banner's decorative ring is a sibling layer over the photo, not an ancestor. */
export const HERO_RING = [{ within: '.dashboard-hero', color: 'rgba(255, 255, 255, .05)' }];
