/**
 * Counter: DOM-only numeric interpolation; no React state updates per frame.
 * API: driver is a mutable 0..1 progress ref, from/to, optional start/end,
 * decimals, suffix and className. Static accessible label is the final value.
 * Reduced motion displays the final value immediately. Creates no ScrollTrigger.
 */
import { useRef } from 'react';
import { gsap, useGSAP, reduceQuery, type Progress } from '../lib/gsap';

type Props = {
  driver: Progress;
  to: number;
  from?: number;
  start?: number;
  end?: number;
  decimals?: number;
  suffix?: string;
  className?: string;
};

export function Counter({
  driver, to, from = 0, start = 0, end = 0.65,
  decimals = 2, suffix = '', className = ''
}: Props) {
  const scope = useRef<HTMLSpanElement>(null);
  useGSAP(() => {
    const media = window.matchMedia(reduceQuery);
    let previous = '';
    const render = () => {
      const p = media.matches ? 1 : gsap.utils.clamp(0, 1, (driver.current - start) / Math.max(0.001, end - start));
      const next = `${(from + (to - from) * p).toFixed(decimals)}${suffix}`;
      if (scope.current && next !== previous) {
        scope.current.textContent = next;
        previous = next;
      }
    };
    render();
    gsap.ticker.add(render);
    return () => gsap.ticker.remove(render);
  }, { scope, dependencies: [driver, from, to, start, end, decimals, suffix] });
  return (
    <span className={className} role="img" aria-label={`${to.toFixed(decimals)}${suffix}`}>
      <span ref={scope} aria-hidden="true">{to.toFixed(decimals)}{suffix}</span>
    </span>
  );
}
