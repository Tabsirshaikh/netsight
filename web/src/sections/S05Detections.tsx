import { useRef } from 'react';
import { content } from '../content';
import { partB } from '../content.partB';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { Counter } from '../components/Counter';
import { Badge } from '../components/Badge';
import { SonarArtwork, type SonarVariant } from '../components/SonarArtwork';
import '../styles.partB.css';

const variants: SonarVariant[] = ['wreck', 'person', 'pot', 'contact', 'mine'];

export function S05Detections() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s05;
  const b = partB.detections;

  useGSAP(() => {
    const root = scope.current!;
    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => { progress.current = 1; });
    mm.add(motionQuery, () => {
      const pin = window.matchMedia('(min-width: 900px) and (min-height: 700px)').matches;
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root,
          pin: pin ? root.querySelector('.section-stage') : false,
          start: pin ? 'top top' : 'top 65%',
          end: pin ? '+=180%' : 'bottom 85%',
          scrub: .65,
          anticipatePin: 1
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.detection-tile', { y: 25, autoAlpha: .35, duration: .22, stagger: .09 }, 0)
        .from('.detection-box path', { drawSVG: '0%', duration: .27, stagger: .026 }, .08)
        .fromTo('.sonar-sweep', { y: -65 }, { y: 335, duration: .65, stagger: .025 }, .04)
        .from('.detection-summary', { y: 15, autoAlpha: 0, duration: .2 }, .78);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="04" className="partb-section detections-section">
      <div className="section-heading partb-heading">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h2 id={`${c.id}-title`}>{c.title}</h2>
          <p className="body-copy">{c.intro}</p>
        </div>
        <div className="partb-heading-aside">
          <Badge />
          <p className="body-copy">{partB.common.artwork}</p>
        </div>
      </div>

      <div className="detection-grid">
        {c.results.map((result, i) => (
          <article className="detection-tile" key={result.dataset}>
            <SonarArtwork
              variant={variants[i]!}
              file={b.files[i]!}
              label={`${b.descriptions[i]} ${partB.common.illustration}`}
            />
            <div className="detection-meta">
              <p className="mono">{result.dataset}</p>
              <h3>{result.target}</h3>
              <div className="detection-score">
                <Counter driver={progress} to={result.value} start={i * .09} end={.42 + i * .09} className="score" />
                <small>{content.ui.ap50}</small>
              </div>
              {'specialist' in result && (
                <>
                  <div className="detection-specialist">
                    <span aria-hidden="true">{partB.common.arrow}</span>
                    <Counter driver={progress} from={result.value} to={result.specialist} start={.66} end={.94} />
                    <span>{content.ui.ap50}</span>
                  </div>
                  <span className="detection-specialist-label">{partB.common.specialist}</span>
                </>
              )}
            </div>
          </article>
        ))}
      </div>

      <div className="detection-summary">
        <div>
          <p className="mono partb-label">{partB.common.average}</p>
          <div className="detection-averages" aria-label={c.summary}>
            <span><strong>{c.previousAverage.toFixed(2)}</strong><small>{partB.common.previous}</small></span>
            <span aria-hidden="true">{partB.common.arrow}</span>
            <span className="new"><strong>{c.average.toFixed(2)}</strong><small>{partB.common.current}</small></span>
          </div>
        </div>
        <p>{c.specialist}<br />{c.summary}</p>
      </div>
      <div className="section-bottom mono">
        <span>{b.footer}</span><span>{partB.common.metric}</span>
      </div>
    </SectionShell>
  );
}

export default S05Detections;
