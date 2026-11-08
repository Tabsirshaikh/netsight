import { useRef } from 'react';
import { content } from '../content';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { SceneViewport } from '../components/SceneViewport';

export function S03Pipeline() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s03;
  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 0.5; });
    mm.add(motionQuery, () => {
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root, pin: root.querySelector('.section-stage'),
          start: 'top top', end: '+=330%', scrub: 0.8, anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.pipeline-visual', { autoAlpha: 0.4, scale: 0.92, duration: 0.15 }, 0)
        .from('.assembly-label', { autoAlpha: 0, y: 10, duration: 0.08 }, 0.91);
      root.querySelectorAll('.pipeline-step').forEach((step, i) => {
        const at = 0.22 + i * 0.095;
        timeline.fromTo(step, { autoAlpha: 0.38, x: 0 }, { autoAlpha: 1, x: 8, duration: 0.04 }, at)
          .to(step, { autoAlpha: 0.52, x: 0, duration: 0.04 }, at + 0.085);
      });
      timeline.to('.pipeline-step', { autoAlpha: 1, x: 0, duration: 0.1 }, 0.88);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="02" className="pipeline-section">
      <div className="section-heading pipeline-heading">
        <p className="eyebrow">{c.eyebrow}</p>
        <h2 id={`${c.id}-title`}>{c.title}</h2>
        <p className="body-copy">{c.intro}</p>
      </div>
      <SceneViewport kind="pipeline" progress={progress} className="pipeline-visual" label={c.description} />
      <ol className="pipeline-list">
        {c.steps.map((step, i) => (
          <li className="pipeline-step" key={step.name}>
            <span className="step-number mono">0{i + 1}</span>
            <div><h3>{step.name}<span>{step.short}</span></h3><p>{step.text}</p></div>
          </li>
        ))}
      </ol>
      <div className="assembly-label mono"><span className="status-dot" />{c.assembly}</div>
      <div className="section-bottom mono"><span>{c.footer}</span><span>{content.ui.illustration}</span></div>
    </SectionShell>
  );
}
