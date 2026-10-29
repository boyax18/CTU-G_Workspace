import type { CSSProperties, ReactNode } from 'react';
import { useInView } from '../../hooks/useInView';

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** Stagger delay in milliseconds. */
  delay?: number;
  as?: 'div' | 'li';
  id?: string;
  /** Where the content slides in from. Left/right fall back to "up" on narrow screens. */
  direction?: 'up' | 'left' | 'right';
}

/**
 * Fades and lifts its content into place every time it scrolls into view (up or down).
 * Put it directly on glass surfaces (not around them) so backdrop blur stays intact.
 */
export default function Reveal({ children, className = '', delay = 0, as = 'div', id, direction = 'up' }: RevealProps) {
  const [ref, inView] = useInView<HTMLDivElement>({ rootMargin: '0px 0px -8% 0px', threshold: 0.1, replay: true });
  const Tag = as as 'div';
  return (
    <Tag
      ref={ref}
      id={id}
      data-dir={direction}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
      className={`reveal ${inView ? 'is-visible' : ''} ${className}`}
    >
      {children}
    </Tag>
  );
}
