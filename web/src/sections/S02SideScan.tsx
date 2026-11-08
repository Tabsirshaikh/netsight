import { useRef } from 'react';
import { content } from '../content';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { SceneViewport } from '../components/SceneViewport';

export function S02SideScan() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s02;
  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 1; });
    mm.add(motionQuery, () => {
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root, pin: root.querySelector('.section-stage'),
          start: 'top top', end: '+=230%', scrub: 0.6, anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.sonar-frame', { y: 45, scale: 0.96, autoAlpha: 0.3, duration: 0.18 }, 0)
        .from('.sonar-annotations path', { drawSVG: '0%', duration: 0.35, stagger: 0.09 }, 0.35)
        .from('.sonar-annotation', { autoAlpha: 0, y: 8, duration: 0.2, stagger: 0.09 }, 0.4);
      root.querySelectorAll('.sonar-phase').forEach((phase, i) => {
        timeline.fromTo(phase, { autoAlpha: 0.35 }, { autoAlpha: 1, duration: 0.16 }, i * 0.27);
      });
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="01" className="sonar-section">
      <div className="section-heading sonar-heading">
        <p className="eyebrow">{c.eyebrow}</p>
        <h2 id={`${c.id}-title`}>{c.title}</h2>
        <p className="body-copy">{c.intro}</p>
      </div>
      <div className="sonar-frame">
        <div className="sonar-frame-top mono"><span>{c.port}</span><span>{c.starboard}</span></div>
        <SceneViewport kind="sonar" progress={progress} label={c.description} />
        <svg className="sonar-annotations" viewBox="0 0 900 600" fill="none" aria-hidden="true">
          <path d="M210 300H135V385H65" />
          <path d="M656 227H735V180H825" />
          <path d="M450 330V485H555" />
          <circle cx="210" cy="300" r="4" /><circle cx="656" cy="227" r="4" /><circle cx="450" cy="330" r="4" />
        </svg>
        <span className="sonar-annotation net-annotation mono">{c.net}</span>
        <span className="sonar-annotation trap-annotation mono">{c.trap}</span>
        <span className="sonar-annotation nadir-annotation mono">{c.nadir}</span>
        <div className="sonar-frame-bottom mono"><span className="status-dot" />{c.line}</div>
      </div>
      <ol className="sonar-phases">
        {c.phases.map((phase, i) => (
          <li key={phase.name} className="sonar-phase">
            <span className="mono phase-index">0{i + 1}</span><div><h3>{phase.name}</h3><p>{phase.text}</p></div>
          </li>
        ))}
      </ol>
      <div className="section-bottom mono"><span>{c.nadirExplanation}</span><span>{c.footer}</span></div>
    </SectionShell>
  );
}
