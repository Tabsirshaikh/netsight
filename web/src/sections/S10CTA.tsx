import { useRef } from 'react';
import { content } from '../content';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { SceneViewport } from '../components/SceneViewport';

export function S10CTA() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s10;
  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 1; });
    mm.add(motionQuery, () => {
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root, pin: root.querySelector('.section-stage'),
          start: 'top top', end: '+=100%', scrub: 0.7, anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.cta-content h2', { y: 36, autoAlpha: 0.3, duration: 0.3 }, 0)
        .from('.cta-action-group', { y: 22, autoAlpha: 0, duration: 0.25 }, 0.2)
        .from('.cta-credits', { y: 18, autoAlpha: 0, duration: 0.25 }, 0.55);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="09" className="cta-section">
      <SceneViewport kind="beacon" progress={progress} label={c.description} />
      <div className="cta-shade" aria-hidden="true" />
      <div className="cta-content">
        <p className="eyebrow">{c.eyebrow}</p>
        <h2 id={`${c.id}-title`}>{c.title}</h2>
        <p className="body-copy">{c.intro}</p>
        <div className="cta-action-group">
          <a className="primary-button" href="/app"><span>{c.action}</span><span className="button-arrow" aria-hidden="true">↗</span></a>
          <span className="mono">{c.actionNote}</span>
        </div>
        <div className="cta-credits"><span className="mono">{c.teamLabel}</span><strong>{content.team}</strong><span>{c.signature}</span></div>
      </div>
      <footer className="story-footer">
        <a href="#mission" className="wordmark">{content.brand}<span className="brand-dot" /></a>
        <span className="mono">{c.footer}</span>
        <a href="#mission" className="mono">{c.top} ↑</a>
      </footer>
    </SectionShell>
  );
}
