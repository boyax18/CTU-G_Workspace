
import { useEffect, useRef, useState } from 'react';

export function useScrollHeader() {
  const [scrolled, setScrolled] = useState(false);
  const progressRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const updateScroll = () => {
      const scrollTop = window.scrollY;
      const maxScroll =
        document.documentElement.scrollHeight - window.innerHeight;

      setScrolled(scrollTop > 12);

      const progress =
        maxScroll > 0 ? Math.min(scrollTop / maxScroll, 1) : 0;

      if (progressRef.current) {
        progressRef.current.style.width = `${progress * 100}%`;
      }
    };

    updateScroll();
    window.addEventListener('scroll', updateScroll, { passive: true });
    window.addEventListener('resize', updateScroll);

    return () => {
      window.removeEventListener('scroll', updateScroll);
      window.removeEventListener('resize', updateScroll);
    };
  }, []);

  return { scrolled, progressRef };
}
