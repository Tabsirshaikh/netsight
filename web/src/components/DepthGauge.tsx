/**
 * DepthGauge API: mount once AFTER sections. Normalised story depth, not bathymetry.
 * Only the endpoints carry a depth label. It does not invent measured depths.
 */
import { useRef } from 'react';
import { gsap, ScrollTrigger, useGSAP } from '../lib/gsap';
import { content } from '../content';

export function DepthGauge() {
  const scope = useRef<HTMLElement>(null);
  useGSAP(() => {
    const fill = scope.current!.querySelector('.depth-fill');
    const marker = scope.current!.querySelector('.depth-marker');
    ScrollTrigger.create({
      start: 0,
      end: () => Math.max(1, ScrollTrigger.maxScroll(window)),
      onUpdate: self => {
        gsap.set(fill, { scaleY: self.progress });
        gsap.set(marker, { y: self.progress * 148 });
        scope.current?.setAttribute('aria-valuenow', String(Math.round(self.progress * 100)));
      }
    });
  }, { scope });
  return (
    <aside ref={scope} className="depth-gauge" role="progressbar"
      aria-label={content.ui.depthLabel} aria-valuemin={0} aria-valuemax={100} aria-valuenow={0}>
      <span>{content.ui.surface}</span>
      <div className="depth-track"><i className="depth-fill" /><b className="depth-marker" /></div>
      <span>{content.ui.bottom}</span>
    </aside>
  );
}
