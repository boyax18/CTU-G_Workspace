import { useEffect, useRef, useState } from 'react';
import { ArrowUpIcon } from './Icons';
import { scrollToSection } from '../../utils/scroll';

const RADIUS = 19;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** Floating back-to-top button whose ring fills with the page scroll progress. */
export default function ScrollToTop() {
  const ringRef = useRef<SVGCircleElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const y = window.scrollY;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const progress = max > 0 ? Math.min(1, y / max) : 0;
      ringRef.current?.style.setProperty('stroke-dashoffset', String(CIRCUMFERENCE * (1 - progress)));
      setVisible(y > 400);
    };
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(update);
    };
    update();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <button
      type="button"
      className="to-top"
      data-visible={visible}
      aria-label="Back to top"
      tabIndex={visible ? 0 : -1}
      onClick={() => scrollToSection('home')}
    >
      <svg className="to-top-ring" viewBox="0 0 44 44" aria-hidden>
        <circle className="to-top-track" cx="22" cy="22" r={RADIUS} />
        <circle
          ref={ringRef}
          className="to-top-bar"
          cx="22"
          cy="22"
          r={RADIUS}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={CIRCUMFERENCE}
        />
      </svg>
      <ArrowUpIcon width={18} height={18} />
    </button>
  );
}
