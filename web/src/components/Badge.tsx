/**
 * Badge API: level = calibrated | indicative | withdrawn | research;
 * optional children override visible wording. Colors are not the only signal.
 */
import { useRef, type ReactNode } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';

export type ClaimLevel = 'calibrated' | 'indicative' | 'withdrawn';
export function Badge({ level = 'research', children }: {
  level?: ClaimLevel | 'research';
  children?: ReactNode;
}) {
  const scope = useRef<HTMLSpanElement>(null);
  useGSAP(() => {}, { scope });
  return (
    <span ref={scope} className={`badge badge-${level}`}>
      <span aria-hidden="true" className="badge-mark">{level === 'withdrawn' ? '×' : level === 'indicative' ? '~' : '+'}</span>
      {children ?? (level === 'research' ? content.ui.research : level)}
    </span>
  );
}
