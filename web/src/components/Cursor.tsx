/**
 * Cursor API: mount once. Native cursor is retained for accessibility.
 * A decorative follower responds to links/buttons. Disabled on touch/reduced motion.
 */
import { useRef } from 'react';
import { gsap, useGSAP } from '../lib/gsap';

export function Cursor() {
  const scope = useRef<HTMLDivElement>(null);
  useGSAP(() => {
    const mm = gsap.matchMedia();
    mm.add('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)', () => {
      const element = scope.current!;
      const x = gsap.quickTo(element, 'x', { duration: 0.22, ease: 'power3' });
      const y = gsap.quickTo(element, 'y', { duration: 0.22, ease: 'power3' });
      const move = (event: PointerEvent) => {
        x(event.clientX);
        y(event.clientY);
        gsap.set(element, { autoAlpha: 1 });
      };
      const over = (event: PointerEvent) => {
        const target = event.target instanceof Element ? event.target : null;
        element.classList.toggle('is-interactive', !!target?.closest('a, button, summary, input'));
      };
      const leave = () => gsap.set(element, { autoAlpha: 0 });
      window.addEventListener('pointermove', move, { passive: true });
      window.addEventListener('pointerover', over, { passive: true });
      document.addEventListener('pointerleave', leave);
      return () => {
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerover', over);
        document.removeEventListener('pointerleave', leave);
      };
    });
    return () => mm.revert();
  }, { scope });
  return <div ref={scope} className="custom-cursor" aria-hidden="true"><i /><b /></div>;
}
