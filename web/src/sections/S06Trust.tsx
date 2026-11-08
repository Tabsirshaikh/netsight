import { useRef } from 'react';
import { content } from '../content';
import { partB } from '../content.partB';
import { gsap, Flip, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { SectionShell } from '../components/SectionShell';
import { Badge } from '../components/Badge';
import { Counter } from '../components/Counter';
import { OptionalAsset } from '../components/OptionalAsset';
import '../styles.partB.css';

export function S06Trust() {
  const scope = useRef<HTMLElement>(null);
  const progress = useRef(0);
  const c = content.s06;
  const b = partB.trust;

  const { contextSafe } = useGSAP({ scope });

  useGSAP(() => {
    const root = scope.current!;
    const card = root.querySelector<HTMLElement>('.trust-survey')!;
    const docks = Array.from(root.querySelectorAll<HTMLElement>('.trust-dock'));
    let currentLevel = 0;
    let flip: ReturnType<typeof Flip.from> | undefined;
    const moveCard = contextSafe((next: number, animate: boolean) => {
      if (next === currentLevel && card.parentElement === docks[next]) return;
      flip?.kill();
      const state = Flip.getState(card);
      docks[next]!.appendChild(card);
      card.dataset.level = c.levels[next]!.name;
      currentLevel = next;
      if (animate) {
        flip = Flip.from(state, {
          duration: .42,
          ease: 'power2.out',
          scale: true,
          absolute: true,
          prune: true
        });
      } else {
        gsap.set(card, { clearProps: 'transform,position,width,height,top,left' });
      }
    });
    const mm = gsap.matchMedia();

    mm.add(reduceQuery, () => {
      progress.current = 1;
      moveCard(0, false);
      gsap.set('.reliability-bar', { scaleY: 1 });
      return () => { flip?.kill(); };
    });

    mm.add(motionQuery, () => {
      const pin = window.matchMedia('(min-width: 900px) and (min-height: 700px)').matches;
      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root,
          pin: pin ? root.querySelector('.section-stage') : false,
          start: pin ? 'top top' : 'top 65%',
          end: pin ? '+=220%' : 'bottom 85%',
          scrub: .65,
          anticipatePin: 1,
          onUpdate: self => {
            const p = self.progress;
            const next = p < .23 ? 0 : p < .45 ? 1 : p < .7 ? 2 : 0;
            moveCard(next, pin);
          }
        }
      });
      timeline.to(progress, { current: 1, duration: 1 }, 0)
        .from('.trust-level', { y: 12, autoAlpha: .35, duration: .22, stagger: .05 }, 0)
        .from('.reliability-bar', {
          scaleY: (index: number) => [.36, .48, .6, .7, .76][index] ?? .5,
          duration: .43,
          stagger: .025,
          transformOrigin: '50% 100%'
        }, .26)
        .from('.budget-cell', { scaleX: 0, transformOrigin: 'left', duration: .12, stagger: .009 }, .65)
        .from('.trust-error-block', { y: 12, autoAlpha: 0, duration: .2 }, .72);

      return () => {
        flip?.kill();
        docks[0]!.appendChild(card);
        card.dataset.level = c.levels[0].name;
        currentLevel = 0;
      };
    });
    return () => {
      mm.revert();
      flip?.kill();
      docks[0]!.appendChild(card);
    };
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="05" className="partb-section trust-section">
      <div className="section-heading partb-heading">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h2 id={`${c.id}-title`}>{c.title}</h2>
        </div>
        <div className="partb-heading-aside">
          <Badge /><p className="body-copy">{c.intro}</p>
        </div>
      </div>

      <div className="trust-layout">
        <div className="trust-gate partb-panel">
          <OptionalAsset file={b.file} />
          <p className="mono partb-label">{b.survey}</p>
          <div className="trust-docks" aria-hidden="true">
            {c.levels.map((level, i) => (
              <div className="trust-dock" key={level.name}>
                {i === 0 && (
                  <div className="trust-survey" data-level="calibrated">
                    <svg viewBox="0 0 140 100">
                      <defs>
                        <pattern id="trust-return-lines" width="8" height="6" patternUnits="userSpaceOnUse">
                          <path d="M0 2H8" stroke="#8ec6a6" strokeOpacity=".35" />
                        </pattern>
                      </defs>
                      <rect width="140" height="100" fill="url(#trust-return-lines)" />
                      <rect x="65" width="10" height="100" fill="#020e14" />
                      <g className="survey-geometry">
                        <path d="M26 27H50V66H26Z" fill="none" stroke="#cfdfb7" strokeWidth="2" />
                        <path d="M32 27V66M40 27V66M26 40H50M26 53H50" stroke="#cfdfb7" />
                        <path d="M50 27L61 34V75L50 66Z" fill="#020c13" />
                      </g>
                    </svg>
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="trust-levels">
            {c.levels.map(level => (
              <div className="trust-level" key={level.name}>
                <Badge level={level.name} />
                <p>{level.text}</p>
              </div>
            ))}
          </div>
          <p className="partb-note">{b.schematic}</p>
        </div>

        <div className="reliability-panel partb-panel">
          <h3 className="partb-subtitle">{b.diagramTitle}</h3>
          <div className="reliability-key mono">
            <span><i />{b.raw}</span><span><i />{b.calibrated}</span>
          </div>
          <svg viewBox="0 0 410 225" role="img" aria-label={`${b.diagramNote}. ${c.calibration}`}>
            <path d="M45 12V185H390" fill="none" stroke="#7c9f924d" />
            {[.2, .4, .6, .8, 1].map((p, i) => {
              const x = 45 + p * 320;
              const height = p * 165;
              return (
                <g key={p}>
                  <path d={`M45 ${185 - height}H385`} stroke="#729b8422" />
                  <rect x={x - 14} y={185 - height * ([.36, .48, .6, .7, .76][i] ?? .5)} width="10" height={height * ([.36, .48, .6, .7, .76][i] ?? .5)} fill="#f4ab71" opacity=".3" />
                  <rect className="reliability-bar" x={x} y={185 - height} width="13" height={height} fill="#6de2c3" opacity=".8" />
                </g>
              );
            })}
            <path d="M45 185L365 20" fill="none" stroke="#d6e7da" strokeDasharray="4 5" opacity=".6" />
            <text className="chart-text" x="210" y="216" textAnchor="middle">{b.predicted}</text>
            <text className="chart-text" transform="translate(14 110) rotate(-90)" textAnchor="middle">{b.observed}</text>
          </svg>
          <p className="partb-note">{b.diagramNote}</p>
        </div>
      </div>

      <div className="trust-budget">
        <div>
          <p className="mono partb-label">{b.fixed}</p>
          <div className="trust-budget-number">
            <Counter driver={progress} to={c.budget.fixedHeld} decimals={0} start={.57} end={.88} />
            <small> {b.slash} {c.budget.surveys}</small>
          </div>
          <div className="budget-cells" aria-hidden="true">
            {Array.from({ length: c.budget.surveys }, (_, i) => (
              <span key={i} className={`budget-cell ${i < c.budget.fixedHeld ? 'held' : 'broken'}`} />
            ))}
          </div>
          <p className="partb-note">{b.held}</p>
        </div>
        <div>
          <p className="mono partb-label">{b.counting}</p>
          <div className="trust-budget-number counting">
            <Counter driver={progress} to={c.budget.labelFreeHeld} decimals={0} start={.57} end={.88} />
            <small> {b.slash} {c.budget.surveys}</small>
          </div>
          <div className="budget-cells" aria-hidden="true">
            {Array.from({ length: c.budget.surveys }, (_, i) => (
              <span key={i} className="budget-cell held" />
            ))}
          </div>
          <p className="partb-note">{b.held}</p>
        </div>
        <div className="trust-error-block">
          <p className="mono partb-label">{b.error}</p>
          <div className="trust-error">{c.calibrationError[0].toFixed(3)}–{c.calibrationError[1].toFixed(3)}</div>
          <p>{c.calibration}</p>
        </div>
      </div>

      <p className="sr-only">{c.budgetText}</p>
      <div className="section-bottom mono">
        <span>{b.geometry} → {b.survey}</span><span>{partB.common.illustration}</span>
      </div>
    </SectionShell>
  );
}

export default S06Trust;
