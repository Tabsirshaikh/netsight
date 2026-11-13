import { useEffect, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { api, percent } from './types';
import type { Analysis, AuditPlan, AuditResult, Contact, SurveyImage } from './types';
import './audit.css';

type Box = [number, number, number, number];
type Point = [number, number];
type Decision = boolean | 'skip';

function normalizedBox(start: Point, end: Point): Box {
  return [
    Math.min(start[0], end[0]), Math.min(start[1], end[1]),
    Math.max(start[0], end[0]), Math.max(start[1], end[1]),
  ];
}

function Crop({ image, contact }: { image: SurveyImage; contact: Pick<Contact, 'id' | 'box'> }) {
  const [x0, y0, x1, y1] = contact.box;
  const scale = 80 / Math.max(1, x1 - x0, y1 - y0);
  return (
    <div className="ns-audit-crop" role="img" aria-label={`Crop of ${contact.id} in ${image.name}`}
      style={{
        backgroundImage: `url(${JSON.stringify(image.url)})`,
        backgroundSize: `${image.width * scale}px ${image.height * scale}px`,
        backgroundPosition: `${40 - (x0 + x1) * scale / 2}px ${40 - (y0 + y1) * scale / 2}px`,
      }} />
  );
}

function BoxRect({ box, faint = false }: { box: Box; faint?: boolean }) {
  return <rect x={box[0]} y={box[1]} width={box[2] - box[0]} height={box[3] - box[1]}
    className={faint ? 'ns-audit-box ns-audit-box-faint' : 'ns-audit-box'}
    vectorEffect="non-scaling-stroke" />;
}

function MarkImage({ image, boxes, disabled, onChange }: {
  image: SurveyImage;
  boxes: Box[];
  disabled: boolean;
  onChange: (boxes: Box[]) => void;
}) {
  const [draft, setDraft] = useState<Box | null>(null);
  const drag = useRef<{ pointerId: number; start: Point } | null>(null);
  const [manual, setManual] = useState<Box>([0, 0, image.width, image.height]);

  function point(event: PointerEvent<SVGSVGElement>): Point {
    const bounds = event.currentTarget.getBoundingClientRect();
    return [
      Math.max(0, Math.min(image.width, (event.clientX - bounds.left) / bounds.width * image.width)),
      Math.max(0, Math.min(image.height, (event.clientY - bounds.top) / bounds.height * image.height)),
    ];
  }

  function cancel() {
    drag.current = null;
    setDraft(null);
  }

  return (
    <section className="ns-audit-image" aria-label={`Mark objects in ${image.name}`}>
      <h4>{image.name}</h4>
      <div className="ns-audit-image-stage" style={{ aspectRatio: `${image.width} / ${image.height}` }}>
        <img src={image.url} alt={image.name} draggable={false} />
        <svg viewBox={`0 0 ${image.width} ${image.height}`} preserveAspectRatio="none"
          role="img" aria-label={`Drag to box objects in ${image.name}. Or enter pixel coordinates below.`}
          className={disabled ? 'ns-audit-overlay disabled' : 'ns-audit-overlay'}
          onPointerDown={event => {
            if (disabled || event.button !== 0 || drag.current) return;
            event.preventDefault();
            event.currentTarget.setPointerCapture(event.pointerId);
            const start = point(event);
            drag.current = { pointerId: event.pointerId, start };
            setDraft(normalizedBox(start, start));
          }}
          onPointerMove={event => {
            if (!drag.current || drag.current.pointerId !== event.pointerId) return;
            setDraft(normalizedBox(drag.current.start, point(event)));
          }}
          onPointerUp={event => {
            const current = drag.current;
            if (!current || current.pointerId !== event.pointerId) return;
            const box = normalizedBox(current.start, point(event));
            cancel();
            event.currentTarget.releasePointerCapture(event.pointerId);
            if (!disabled && box[2] > box[0] && box[3] > box[1]) onChange([...boxes, box]);
          }}
          onPointerCancel={cancel} onLostPointerCapture={cancel}>
          {image.detections.filter(d => d.flagged).map(d => <BoxRect key={d.id} box={d.box} faint />)}
          {boxes.map((box, i) => <BoxRect key={i} box={box} />)}
          {draft && <BoxRect box={draft} />}
        </svg>
      </div>
      <p className="ns-micro">Dashed boxes are model flags, for orientation only.</p>
      <ol className="ns-audit-box-list">
        {boxes.map((box, i) => (
          <li key={i}>
            <span>Box {i + 1}: {box.map(n => Math.round(n)).join(', ')} px</span>
            <button type="button" disabled={disabled} aria-label={`Remove box ${i + 1} from ${image.name}`}
              onClick={() => onChange(boxes.filter((_, index) => index !== i))}>Remove</button>
          </li>
        ))}
      </ol>
      <details>
        <summary>Add a box with pixel coordinates</summary>
        <div className="ns-audit-coordinates">
          {(['Left', 'Top', 'Right', 'Bottom'] as const).map((label, i) => (
            <label key={label}>{label}
              <input type="number" min="0" max={i % 2 === 0 ? image.width : image.height}
                step="1" value={manual[i]} disabled={disabled}
                onChange={event => {
                  const value = event.target.valueAsNumber;
                  if (!Number.isFinite(value)) return;
                  setManual(previous => {
                    const next: Box = [...previous];
                    next[i] = Math.max(0, Math.min(i % 2 === 0 ? image.width : image.height, value));
                    return next;
                  });
                }} />
            </label>
          ))}
          <button type="button" disabled={disabled || manual[2] <= manual[0] || manual[3] <= manual[1]}
            onClick={() => onChange([...boxes, [...manual]])}>Add box</button>
        </div>
      </details>
    </section>
  );
}

export function AuditPanel({ result, plan, disabled = false, onProbabilities }: {
  result: Analysis;
  plan: AuditPlan;
  disabled?: boolean;
  onProbabilities: (probabilities: Record<string, number>) => void;
}) {
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const [objects, setObjects] = useState<Record<number, Box[]>>({});
  const [score, setScore] = useState<AuditResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);
  const locked = disabled || running;

  useEffect(() => () => controller.current?.abort(), []);

  const samples = plan.contact_sample.map(id => {
    for (const image of result.images) {
      const contact = image.detections.find(d => d.id === id);
      if (contact) return { id, image, contact };
    }
    // Low-probability candidates are hidden from `detections`; the plan carries their box.
    const saved = plan.contacts?.find(c => c.id === id);
    const image = saved && result.images.find(img => img.index === saved.image);
    if (saved && image) {
      const contact: Pick<Contact, 'id' | 'box' | 'probability' | 'audited'> = {
        id, box: saved.box, probability: saved.probability, audited: false,
      };
      return { id, image, contact };
    }
    return { id, image: undefined, contact: undefined };
  });
  const decided = plan.contact_sample.filter(id => typeof decisions[id] === 'boolean').length;

  async function submit() {
    if (locked || controller.current) return;
    const request = new AbortController();
    controller.current = request;
    setRunning(true);
    setError('');
    try {
      const response = await api<AuditResult>(`/api/packs/${encodeURIComponent(result.survey_id)}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: request.signal,
        body: JSON.stringify({
          contacts: plan.contact_sample.flatMap(id => {
            const real = decisions[id];
            return typeof real === 'boolean' ? [{ id, real }] : [];
          }),
          images: plan.recall_images.map(index => ({ index, objects: objects[index] ?? [] })),
        }),
      });
      if (request.signal.aborted) return;
      setScore(response);
      if (response.calibration.recalibrated && response.calibration.probabilities) {
        onProbabilities(response.calibration.probabilities);
      }
    } catch (err) {
      if (!request.signal.aborted) setError(err instanceof Error ? err.message : 'Could not score the audit.');
    } finally {
      if (!request.signal.aborted) setRunning(false);
      if (controller.current === request) controller.current = null;
    }
  }

  return (
    <section className="ns-audit" aria-label="Operator audit">
      <h2>Operator audit</h2>
      <p className={plan.recommended ? 'ns-audit-notice' : 'ns-muted'}>{plan.reason}</p>

      <section aria-label="Random contact check" className="ns-audit-part">
        <h3>Random contact check</h3>
        <p>Decide every listed contact honestly; the sample is random on purpose - checking only the top contacts would mislead the recalibration.</p>
        <p className="ns-muted" role="status">{decided} of {plan.contact_sample.length} decided</p>
        <ul className="ns-audit-samples">
          {samples.map(({ id, image, contact }) => (
            <li key={id}>
              {image && contact ? <Crop image={image} contact={contact} /> : <span className="ns-muted">Preview not available</span>}
              <div className="ns-audit-contact-info">
                <strong>{image?.name ?? id}</strong>
                <small>{id}</small>
                {contact && <span>P(real): {percent(contact.probability)}{contact.audited && <small className="ns-audited-tag">audited</small>}</span>}
              </div>
              <div className="ns-audit-decisions" role="group" aria-label={`Decision for ${id}`}>
                {([{ label: 'Real', value: true }, { label: 'Not real', value: false }, { label: 'Skip', value: 'skip' }] as const).map(option => (
                  <button type="button" key={option.label} disabled={locked || !contact}
                    aria-pressed={decisions[id] === option.value}
                    onClick={() => setDecisions(previous => ({ ...previous, [id]: option.value }))}>{option.label}</button>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-label="Mark every object" className="ns-audit-part">
        <h3>Mark every object</h3>
        <p>Box every object you can see in this image (object only, not its shadow), including ones the model missed.</p>
        <p className="ns-muted">Validation recall: {percent(plan.validation_recall)}</p>
        {plan.recall_images.map(index => {
          const image = result.images.find(img => img.index === index);
          return image ? (
            <MarkImage key={index} image={image} boxes={objects[index] ?? []} disabled={locked}
              onChange={boxes => setObjects(previous => ({ ...previous, [index]: boxes }))} />
          ) : <p key={index} className="ns-muted">Image {index + 1} is not available.</p>;
        })}
      </section>

      {error && <p className="ns-audit-error" role="alert">{error}</p>}
      <button type="button" className="ns-audit-submit" disabled={locked} onClick={() => void submit()}>
        {running ? 'Scoring…' : 'Score audit'}
      </button>
      <span className="ns-sr-only" role="status">{running ? 'Scoring audit' : score ? 'Audit scored' : ''}</span>

      {score && (
        <div className="ns-audit-results">
          <section className="ns-audit-result-card">
            <h3>Calibration</h3>
            {score.calibration.recalibrated && score.calibration.check && (
              <>
                <p>Shown P(real) averaged {percent(score.calibration.check.predicted)}, audited contacts were {percent(score.calibration.check.observed)} real</p>
                <p className={score.calibration.check.consistent ? '' : 'ns-audit-warning'}>
                  {score.calibration.check.consistent ? 'consistent' : `not consistent (p = ${score.calibration.check.p_value.toPrecision(3)})`}
                </p>
              </>
            )}
            {score.calibration.note && <p>{score.calibration.note}</p>}
          </section>
          <section className="ns-audit-result-card">
            <h3>Recall</h3>
            <p>Marked objects: {score.recall.objects}, found by the model at this survey&apos;s threshold: {score.recall.detected} (recall {percent(score.recall.recall)})</p>
            <p>Validation recall: {percent(score.recall.validation_recall)}</p>
            {score.recall.below_validation === true ? (
              <p className="ns-audit-warning">Recall on this survey is significantly below validation - treat the survey as not fully searched</p>
            ) : score.recall.below_validation === false ? (
              <p>No significant recall drop</p>
            ) : <p>{score.recall.note}</p>}
          </section>
          <section className="ns-audit-result-card">
            <h3>Completeness</h3>
            {score.completeness.available ? (
              <>
                <p>Pd for objects like the ones you marked: {percent(score.completeness.pd)} (90% lower bound {percent(score.completeness.pd_lower90)})</p>
                <p>Trials: {score.completeness.trials ?? '—'}</p>
                <p>{score.completeness.caveat}</p>
              </>
            ) : <p>{score.completeness.reason}</p>}
          </section>
        </div>
      )}
      <a className="ns-audit-download" href={`/api/packs/${encodeURIComponent(result.survey_id)}/audit.json`} download>Download audit.json</a>
    </section>
  );
}
