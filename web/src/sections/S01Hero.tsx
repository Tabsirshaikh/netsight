import { useRef } from 'react';
import { content } from '../content';
import { gsap, useGSAP, SplitText, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { SceneViewport } from '../components/SceneViewport';

export function S01Hero() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s01;

  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 0.58; });
    mm.add(motionQuery, () => {
      const title = new SplitText(root.querySelector('h1')!, { type: 'chars', aria: 'auto' });
      const particles = root.querySelectorAll('.echo-particle');
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root, pin: root.querySelector('.section-stage'),
          start: 'top top', end: '+=210%', scrub: 0.7, anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from(title.chars, {
          x: i => Math.sin(i * 4.2) * 180,
          y: i => Math.cos(i * 2.4) * 100,
          rotation: i => (i % 2 ? 12 : -12),
          autoAlpha: 0.16, stagger: 0.018, duration: 0.22
        }, 0)
        .fromTo(particles, {
          x: i => Math.sin(i * 3.7) * 260,
          y: i => Math.cos(i * 2.3) * 130,
          scale: 1, autoAlpha: 0.8
        }, { x: 0, y: 0, scale: 0, autoAlpha: 0, duration: 0.34, stagger: 0.002 }, 0)
        .from('.hero-copy', { y: 24, autoAlpha: 0.35, duration: 0.2 }, 0.13)
        .to('.surface-caption', { y: -18, autoAlpha: 0, duration: 0.12 }, 0.36)
        .fromTo('.dive-caption', { y: 18, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.15 }, 0.48)
        .to('.hero-horizon', { scaleX: 0.45, autoAlpha: 0.2, duration: 0.4 }, 0.4)
        .from('.hero-next', { y: 18, autoAlpha: 0, duration: 0.15 }, 0.82);
      return () => title.revert();
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="00" className="hero-section">
      <SceneViewport kind="hero" progress={progress} label={c.description} />
      <div className="hero-shade" aria-hidden="true" />
      <div className="hero-topline mono"><span>{c.eyebrow}</span><span>{content.team}</span></div>
      <div className="hero-content">
        <p className="hero-kicker">{c.statement}</p>
        <div className="hero-title-wrap">
          <h1 id={`${c.id}-title`}>{c.title}</h1>
          <div className="echo-cloud" aria-hidden="true">
            {Array.from({ length: 56 }, (_, i) => (
              <i key={i} className="echo-particle" style={{ left: `${4 + (i * 17 % 91)}%`, top: `${15 + (i * 23 % 65)}%` }} />
            ))}
          </div>
        </div>
        <div className="hero-copy"><p>{c.subtitle}</p><span className="mono">{c.targets}</span></div>
      </div>
      <div className="hero-horizon" aria-hidden="true" />
      <div className="hero-coordinate mono">
        <div className="surface-caption"><span className="status-dot" />{c.surfaceLabel}<small>{c.vessel} → {c.towfish}</small></div>
        <div className="dive-caption"><span className="status-dot" />{c.diveLabel}<small>{c.signal}</small></div>
      </div>
      <div className="hero-bottom">
        <a className="scroll-cue mono" href="#side-scan"><span aria-hidden="true">↓</span>{content.ui.scroll}</a>
        <p className="hero-next">{c.next}</p>
        <span className="illustration-label mono">{content.ui.illustration}</span>
      </div>
    </SectionShell>
  );
}
