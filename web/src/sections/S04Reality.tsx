import { useRef } from 'react';
import { content } from '../content';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { SceneViewport } from '../components/SceneViewport';
import { Counter } from '../components/Counter';
import { Badge } from '../components/Badge';

export function S04Reality() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s04;
  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 1; });
    mm.add(motionQuery, () => {
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root, pin: root.querySelector('.section-stage'),
          start: 'top top', end: '+=190%', scrub: 0.7, anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.comparison-column', { y: 20, autoAlpha: 0.25, duration: 0.18, stagger: 0.08 }, 0)
        .from('.comparison-context', { autoAlpha: 0, y: 16, duration: 0.16 }, 0.55)
        .from('.comparison-punchline', { autoAlpha: 0, y: 24, duration: 0.18 }, 0.75)
        .from('.punchline-rule', { scaleX: 0, duration: 0.2 }, 0.77);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="03" className="reality-section">
      <div className="section-heading reality-heading">
        <div><p className="eyebrow">{c.eyebrow}</p><h2 id={`${c.id}-title`}>{c.title}</h2></div>
        <div className="reality-intro"><Badge /><p className="body-copy">{c.intro}</p><span className="mono">{c.metric}</span></div>
      </div>
      <div className="comparison">
        <div className="comparison-values">
          {c.columns.map((column, i) => (
            <div key={column.title} className={`comparison-column ${column.tone}`}>
              <span className="mono comparison-label">0{i + 1} / {column.label}</span>
              <Counter driver={progress} to={column.value} start={i * 0.12} end={0.4 + i * 0.12} className="comparison-number" />
            </div>
          ))}
        </div>
        <SceneViewport kind="comparison" progress={progress} className="comparison-volume" label={c.description} />
        <div className="comparison-captions">
          {c.columns.map(column => (
            <div key={column.title} className={column.tone}>
              <h3>{column.title}</h3><p>{column.caption}</p>
            </div>
          ))}
        </div>
      </div>
      <div className="comparison-conclusion">
        <p className="comparison-context">{c.context}</p>
        <div className="comparison-punchline"><span className="punchline-rule" /><h3>{c.punchline}<br /><em>{c.response}</em></h3></div>
      </div>
      <div className="section-bottom mono"><span>{c.note}</span><span>{content.ui.ap50}</span></div>
    </SectionShell>
  );
}
