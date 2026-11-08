import { useRef } from 'react';
import { content } from '../content';
import { partB } from '../content.partB';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { Badge } from '../components/Badge';
import { Counter } from '../components/Counter';
import { SonarArtwork } from '../components/SonarArtwork';
import '../styles.partB.css';

export function S07Geometry() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s07;
  const b = partB.geometry;

  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => {
      progress.current = 1;
      gsap.set('.geometry-object', { scaleX: 1 });
    });
    mm.add(motionQuery, () => {
      const pin = window.matchMedia('(min-width: 900px) and (min-height: 700px)').matches;
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root,
          pin: pin ? root.querySelector('.section-stage') : false,
          start: pin ? 'top top' : 'top 65%',
          end: pin ? '+=150%' : 'bottom 85%',
          scrub: .65,
          anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .fromTo('.geometry-object', {
          scaleX: 1.8,
          svgOrigin: '222 205'
        }, {
          scaleX: 1,
          duration: .7
        }, .12)
        .from('.geometry-reference', { autoAlpha: 0, duration: .15 }, .62)
        .from('.geometry-no-retrain', { y: 15, autoAlpha: 0, duration: .18 }, .75);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="06" className="partb-section geometry-section">
      <div className="section-heading partb-heading">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h2 id={`${c.id}-title`}>{c.title}</h2>
        </div>
        <div className="partb-heading-aside">
          <Badge /><p className="body-copy">{c.intro}</p>
        </div>
      </div>

      <div className="geometry-layout">
        <div className="geometry-numbers">
          <div className="geometry-number-row">
            <span className="mono">{c.beforeLabel}</span>
            <span className="geometry-number">{c.before.toFixed(3)}</span>
          </div>
          <div className="geometry-number-row after">
            <span className="mono">{c.afterLabel}</span>
            <Counter driver={progress} from={c.before} to={c.after} decimals={3} start={.12} end={.82} className="geometry-number" />
          </div>
          <h3 className="geometry-no-retrain">{b.noRetraining}</h3>
          <p className="partb-note">{partB.common.metric}</p>
        </div>

        <div>
          <div className="geometry-frame">
            <SonarArtwork
              variant="pot"
              geometry
              file={b.file}
              label={`${b.scanLabel}. ${partB.common.illustration}`}
            />
            <div className="geometry-reference" aria-hidden="true" />
            <div className="geometry-ruler mono">
              <span>{c.beforeLabel}</span><span aria-hidden="true">→</span><span>{c.afterLabel}</span>
            </div>
          </div>
          <p className="partb-note geometry-caption">{b.caption}</p>
        </div>
      </div>
      <div className="section-bottom mono">
        <span>{b.instruction}</span><span>{content.ui.ap50}</span>
      </div>
    </SectionShell>
  );
}

export default S07Geometry;
