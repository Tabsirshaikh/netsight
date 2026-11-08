import { useRef } from 'react';
import { content } from '../content';
import { partB } from '../content.partB';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { Badge } from '../components/Badge';
import { Counter } from '../components/Counter';
import '../styles.partB.css';

export function S08Curve() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s08;
  const b = partB.curve;
  const first = c.points[0].recordings;
  const last = c.points[c.points.length - 1]!.recordings;
  const points = c.points.map(point => ({
    ...point,
    x: 100 + (point.recordings - first) / (last - first) * 560,
    y: 360 - point.value * 700
  }));
  const path = points.map((point, i) => `${i === 0 ? 'M' : 'L'}${point.x} ${point.y}`).join(' ');

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
        .from('.learning-path', { drawSVG: '0%', duration: .65 }, .08)
        .from('.curve-point', { autoAlpha: 0, y: 10, duration: .1, stagger: .26 }, .08)
        .from('.recording-tile', {
          autoAlpha: .15,
          scale: .88,
          duration: .12,
          stagger: index => index < 5 ? .08 + index * .012 : index < 10 ? .35 + (index - 5) * .012 : .62 + (index - 10) * .008
        }, 0)
        .from('.sensor-insight', { y: 16, autoAlpha: 0, duration: .2 }, .76);
    });
    return () => mm.revert();
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="07" className="partb-section curve-section">
      <div className="section-heading partb-heading">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h2 id={`${c.id}-title`}>{c.title}</h2>
        </div>
        <div className="partb-heading-aside">
          <Badge /><p className="body-copy">{c.intro}</p>
        </div>
      </div>

      <div className="curve-layout">
        <div className="curve-panel partb-panel">
          <p className="mono partb-label">{b.metric}</p>
          <svg className="curve-chart" viewBox="0 0 760 420" role="img" aria-label={c.notes[0]}>
            <defs>
              <linearGradient id="learning-area" x1="0" y1="0" x2="0" y2="1">
                <stop stopColor="#6de2c3" stopOpacity=".2" />
                <stop offset="1" stopColor="#6de2c3" stopOpacity="0" />
              </linearGradient>
            </defs>
            {b.tickValues.map((tick, i) => (
              <g key={tick}>
                <path d={`M70 ${360 - tick * 700}H705`} fill="none" stroke="#88ae922b" strokeDasharray="3 7" />
                <text x="48" y={365 - tick * 700} textAnchor="end">{b.ticks[i]}</text>
              </g>
            ))}
            <path d="M70 65V360H705" fill="none" stroke="#96b4a766" />
            <path d={`${path}L660 360H100Z`} fill="url(#learning-area)" />
            <path className="learning-path" d={path} stroke="#6de2c3" strokeWidth="3" fill="none" />
            {points.map(point => (
              <g className="curve-point" key={point.recordings}>
                <path d={`M${point.x} ${point.y}V360`} stroke="#6de2c34d" strokeDasharray="4 6" />
                <circle cx={point.x} cy={point.y} r="12" fill="#6de2c3" opacity=".12" />
                <circle cx={point.x} cy={point.y} r="5" fill="#b2f5d7" />
                <text className="curve-value" x={point.x} y={point.y - 27} textAnchor="middle">{point.value.toFixed(2)}</text>
                <text className="curve-count" x={point.x} y="393" textAnchor="middle">{point.recordings}</text>
              </g>
            ))}
          </svg>
          <p className="curve-axis-label mono">{b.recordings}</p>
        </div>

        <div className="recordings-panel partb-panel">
          <div>
            <p className="mono partb-label">{b.tiles}</p>
            <div className="recording-grid" role="img" aria-label={b.mapLabel}>
              {Array.from({ length: last }, (_, i) => (
                <span
                  className="recording-tile"
                  key={i}
                  style={{ transform: `rotate(${((i * 7) % 5) - 2}deg)` }}
                />
              ))}
            </div>
            <p className="partb-note">{b.mapLabel}</p>
          </div>
          <div className="curve-stages">
            {c.points.map((point, i) => (
              <div key={point.recordings}>
                <Counter driver={progress} to={point.recordings} decimals={0} start={i * .27} end={.2 + i * .27} className="mono" />
                <strong>{point.value.toFixed(2)}</strong>
              </div>
            ))}
          </div>
          <div className="sensor-insight">
            <p className="mono partb-label">{b.sensorLabel}</p>
            <h3>{c.sensor}</h3>
            <p className="partb-note">{c.notes[0]}</p>
          </div>
        </div>
      </div>

      <div className="section-bottom mono">
        <span>{b.footer}</span><span>{partB.common.metric}</span>
      </div>
    </SectionShell>
  );
}

export default S08Curve;
