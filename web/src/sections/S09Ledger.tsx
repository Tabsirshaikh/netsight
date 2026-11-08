import { useRef } from 'react';
import { content } from '../content';
import { illustrativeEvidence, partB } from '../content.partB';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';
import { alterIllustration, firstBrokenRecord, makeIllustrativeLedger } from '../lib/illustrativeLedger';
import { SectionShell } from '../components/SectionShell';
import { Badge } from '../components/Badge';
import { OptionalAsset } from '../components/OptionalAsset';
import '../styles.partB.css';

const illustrativeJson = `data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(illustrativeEvidence, null, 2))}`;

export function S09Ledger() {
  const scope = useRef<HTMLElement>(null);
  const c = content.s09;
  const b = partB.ledger;

  useGSAP(() => {
    const root = scope.current!;
    const chain = root.querySelector<HTMLElement>('.ledger-chain')!;
    const blocks = Array.from(root.querySelectorAll<HTMLElement>('.ledger-block'));
    const status = root.querySelector<HTMLElement>('.ledger-status')!;
    const action = root.querySelector<HTMLButtonElement>('.ledger-alter')!;
    const hashes = Array.from(root.querySelectorAll<HTMLElement>('.ledger-hash'));
    let alive = true;
    let ready = false;
    let failed = false;
    let scrollTampered = false;
    let override: boolean | null = null;
    let lastApplied: boolean | null = null;
    let brokenIndex = 1;

    const paint = () => {
      if (!alive) return;
      const tampered = override ?? scrollTampered;
      if (!ready) {
        status.textContent = failed ? b.unavailable : b.working;
        return;
      }
      if (lastApplied === tampered) return;
      lastApplied = tampered;
      chain.dataset.tampered = String(tampered);
      blocks.forEach((block, i) => {
        block.classList.toggle('is-broken', tampered && i >= brokenIndex);
      });
      status.textContent = tampered ? c.tampered : c.valid;
      action.textContent = tampered ? b.original : b.change;
      action.setAttribute('aria-pressed', String(tampered));
    };

    const toggle = () => {
      override = !(override ?? scrollTampered);
      paint();
    };
    action.addEventListener('click', toggle);
    action.disabled = true;

    void makeIllustrativeLedger().then(async records => {
      const [originalBroken, changedBroken] = await Promise.all([
        firstBrokenRecord(records),
        firstBrokenRecord(alterIllustration(records))
      ]);
      if (!alive) return;
      if (originalBroken !== -1 || changedBroken < 0) throw new Error('Illustration verification failed');
      brokenIndex = changedBroken;
      hashes.forEach((element, i) => {
        const hash = records[i]!.hash;
        element.textContent = `${hash.slice(0, 12)}…${hash.slice(-8)}`;
        element.title = hash;
      });
      ready = true;
      action.disabled = false;
      paint();
    }).catch(() => {
      if (!alive) return;
      failed = true;
      paint();
    });

    const mm = gsap.matchMedia();
    mm.add(reduceQuery, () => {
      scrollTampered = false;
      paint();
    });
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
          anticipatePin: 1,
          onUpdate: self => {
            scrollTampered = self.progress > .77;
            paint();
          }
        }
      });
      timeline
        .from('.report-field', { y: 15, autoAlpha: 0, duration: .16, stagger: .065 }, 0)
        .from('.ledger-block', { x: 24, autoAlpha: 0, duration: .16, stagger: .11 }, .12)
        .from('.ledger-disclaimer', { y: 12, autoAlpha: 0, duration: .15 }, .8);
      // A final hold gives the altered link time to be inspected.
      timeline.to({}, { duration: .15 }, .95);
    });

    return () => {
      alive = false;
      mm.revert();
      action.removeEventListener('click', toggle);
    };
  }, { scope });

  return (
    <SectionShell ref={scope} id={c.id} index="08" className="partb-section ledger-section">
      <div className="section-heading partb-heading">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h2 id={`${c.id}-title`}>{c.title}</h2>
        </div>
        <div className="partb-heading-aside">
          <Badge /><p className="body-copy">{c.intro}</p>
        </div>
      </div>

      <div className="ledger-layout">
        <article className="evidence-report partb-panel">
          <OptionalAsset file={b.file} />
          <div className="report-topline">
            <h3>{b.report}</h3><span className="mono partb-label">{content.brand}</span>
          </div>
          <ol className="report-fields">
            {c.fields.map((field, i) => (
              <li className="report-field" key={field}>
                <span className="mono" aria-hidden="true">0{i + 1}</span>{field}
              </li>
            ))}
          </ol>
          <a className="partb-button" href={illustrativeJson} download={b.exportName}>{b.download} ↗</a>
          <p className="partb-note">{b.reportType}<br />{b.emptyProbability}</p>
        </article>

        <div className="ledger-chain" data-tampered="false">
          <p className="mono partb-label">{b.fingerprint}</p>
          <div className="ledger-records">
            {b.payloadNames.map((name, i) => (
              <div className="ledger-block" key={name}>
                <div className="ledger-block-header">
                  <h3>{name}</h3><span className="mono">{b.record} / 0{i + 1}</span>
                </div>
                <code className="ledger-hash">{b.working}</code>
              </div>
            ))}
          </div>
          <p className="ledger-status mono" role="status" aria-live="polite">{b.working}</p>
          <div className="ledger-controls">
            <button type="button" className="partb-button ledger-alter" aria-pressed="false">{b.change}</button>
            <span className="partb-note">{b.illustration}</span>
          </div>
        </div>
      </div>
      <p className="ledger-disclaimer">{c.disclaimer}</p>
      <div className="section-bottom mono">
        <span>{b.linked}</span><span>{partB.common.illustration}</span>
      </div>
    </SectionShell>
  );
}

export default S09Ledger;
