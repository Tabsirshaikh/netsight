import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { gsap, useGSAP } from '../lib/gsap';
import { Viewer } from './Viewer';
import { CommandPalette } from './CommandPalette';
import type { Command } from './CommandPalette';
import { api, operatingPreview, percent, profiles } from './types';
import type { Analysis, Contact, Health, ModelKey, Profile, Sample, Session } from './types';
import './dashboard.css';

const START = 'uv run python -m netsight.app.server --port 8000';
const STAGES = ['Detecting contacts', 'Measuring evidence', 'Calibrating probabilities', 'Checking applicability', 'Writing evidence pack'];

function Evidence({ contact }: { contact: Contact }) {
  const entries = Object.entries(contact.evidence);
  if (!entries.length) {
    return <p className="ns-muted">Evidence is measured for contacts flagged in the saved run. Re-run at this budget to measure newly flagged contacts.</p>;
  }
  function format(value: unknown): string {
    if (value === null || value === undefined) return 'not measured';
    if (typeof value === 'boolean') return value ? 'yes' : 'no';
    if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(3);
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }
  const shadow = entries.find(([key]) => key === 'shadow_present' || key === 'has_shadow');
  return (
    <div className="ns-evidence">
      {shadow?.[1] === false && <p className="ns-shadow-note">No measurable shadow (not penalised)</p>}
      <dl>{entries.map(([key, value]) => (
        <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd title={format(value)}>{format(value)}</dd></div>
      ))}</dl>
      <p className="ns-micro">Image evidence is descriptive, not proof of identity. Height is shown only when measured by the evidence extractor.</p>
    </div>
  );
}

function Running() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setStage(s => Math.min(STAGES.length - 1, s + 1)), 3500);
    return () => window.clearInterval(timer);
  }, []);
  return (
    <div className="ns-running" role="status" aria-live="polite">
      <div className="ns-sonar" aria-hidden="true"><i /><i /><i /><b /><span>⌁</span></div>
      <p className="ns-eyebrow">SURVEY IN PROGRESS</p>
      <h2>{STAGES[stage]}</h2>
      <p>Keep this workspace open. First use also loads the research models.</p>
      <div className="ns-stages">{STAGES.map((label, i) => <span key={label} className={i <= stage ? 'active' : ''} title={label} />)}</div>
      <small>Stage captions are illustrative; the API returns one completed survey.</small>
    </div>
  );
}

export default function Dashboard() {
  const root = useRef<HTMLDivElement>(null);
  const contactCard = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const objectUrls = useRef(new Set<string>());
  const requestController = useRef<AbortController | null>(null);
  const alive = useRef(true);
  const [health, setHealth] = useState<Health | null>(null);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [connectionError, setConnectionError] = useState('');
  const [error, setError] = useState('');
  const [connecting, setConnecting] = useState(true);
  const [files, setFiles] = useState<File[]>([]);
  const [sampleIds, setSampleIds] = useState<string[]>([]);
  const [model, setModel] = useState<ModelKey>('general');
  const [profile, setProfile] = useState<Profile>('general');
  const [budget, setBudget] = useState(1);
  const [tta, setTta] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [imageIndex, setImageIndex] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [sort, setSort] = useState<'probability' | 'raw_score'>('probability');
  const [descending, setDescending] = useState(true);
  const [zoomRequest, setZoomRequest] = useState(0);
  const [palette, setPalette] = useState(false);

  const session = sessions.find(s => s.result.survey_id === activeId);
  const result = session?.result;
  const image = result?.images[imageIndex];
  const preview = useMemo(() => result ? operatingPreview(result, budget) : null, [result, budget]);
  const allContacts = useMemo(() => result?.images.flatMap(img =>
    img.detections.map(contact => ({ ...contact, imageIndex: img.index, imageName: img.name }))) || [], [result]);
  const contacts = useMemo(() => [...allContacts].sort((a, b) =>
    (descending ? -1 : 1) * (a[sort] - b[sort]) || a.id.localeCompare(b.id)), [allContacts, sort, descending]);
  const contact = allContacts.find(c => c.id === selected);
  const localBudget = !!result && budget !== result.operating.budget;
  const staleControls = !!result && (model !== session?.model || profile !== result.profile || tta !== result.tta);
  const currentModel = health?.models.find(m => m.key === (session?.model || model));
  const modelClass = result?.model.model_class || currentModel?.model_class || 'research';

  const connect = useCallback(async () => {
    setConnecting(true);
    setConnectionError('');
    try {
      const status = await api<Health>('/api/health');
      if (!alive.current) return;
      setHealth(status);
      const gallery = await api<{ samples: Sample[] }>('/api/samples');
      if (alive.current) setSamples(gallery.samples);
    } catch (err) {
      if (alive.current) setConnectionError(err instanceof Error ? err.message : 'Could not reach the API.');
    } finally {
      if (alive.current) setConnecting(false);
    }
  }, []);

  useEffect(() => {
    alive.current = true;
    void connect();
    return () => {
      alive.current = false;
      requestController.current?.abort();
      objectUrls.current.forEach(url => URL.revokeObjectURL(url));
      objectUrls.current.clear();
    };
  }, [connect]);

  function chooseContact(id: string) {
    const next = allContacts.find(c => c.id === id);
    if (next) { setSelected(id); setImageIndex(next.imageIndex); }
  }

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPalette(open => !open);
        return;
      }
      if (palette || busy || event.metaKey || event.ctrlKey || event.altKey) return;
      const element = event.target as HTMLElement;
      if (element.closest('input, select, textarea, [contenteditable="true"]')) return;
      if (event.key === 'j' || event.key === 'k') {
        event.preventDefault();
        if (!contacts.length) return;
        const position = contacts.findIndex(c => c.id === selected);
        const next = position < 0 ? 0 : (position + (event.key === 'j' ? 1 : -1) + contacts.length) % contacts.length;
        const item = contacts[next];
        setSelected(item.id);
        setImageIndex(item.imageIndex);
      }
      if (event.key === 'Enter' && selected && !element.closest('button, a')) {
        event.preventDefault();
        setZoomRequest(n => n + 1);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [palette, busy, contacts, selected]);

  useGSAP(() => {
    if (!contactCard.current || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    gsap.fromTo(contactCard.current, { y: 6, opacity: 0.35 }, { y: 0, opacity: 1, duration: 0.25, ease: 'power2.out' });
  }, { scope: root, dependencies: [selected], revertOnUpdate: true });

  function addFiles(incoming: File[]) {
    setError('');
    const valid = incoming.every(file => /\.(png|jpe?g|tiff?|bmp)$/i.test(file.name));
    if (!valid) { setError('Choose PNG, JPG, TIF, TIFF or BMP files. Multiple images form one survey.'); return; }
    const next = [...files, ...incoming];
    if (next.length + sampleIds.length > 20) { setError('A survey can contain up to 20 images.'); return; }
    if (next.reduce((sum, file) => sum + file.size, 0) > 50 * 1024 * 1024 - 128 * 1024) {
      setError('Keep the combined uploads below 50 MB, including multipart request overhead.');
      return;
    }
    setFiles(next);
  }

  function toggleSample(id: string) {
    setError('');
    if (sampleIds.includes(id)) setSampleIds(ids => ids.filter(s => s !== id));
    else if (sampleIds.length + files.length >= 20) setError('A survey can contain up to 20 images.');
    else setSampleIds(ids => [...ids, id]);
  }

  async function runSurvey() {
    if (busy || !files.length && !sampleIds.length) return;
    setError('');
    setBusy(true);
    const controller = new AbortController();
    requestController.current = controller;
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    sampleIds.forEach(id => form.append('sample_ids', id));
    form.set('model', model);
    form.set('profile', profile);
    form.set('budget', String(budget));
    form.set('tta', String(tta));
    form.set('show_all', String(showAll));
    const newUrls: string[] = [];
    try {
      const analysis = await api<Analysis>('/api/analyze', { method: 'POST', body: form, signal: controller.signal });
      // Server-generated greyscale PNG previews also support browser-incompatible TIFFs.
      for (const img of analysis.images) {
        const response = await fetch(img.url, { signal: controller.signal });
        if (!response.ok) throw new Error('The survey completed, but a PNG preview could not be loaded. Check the API and re-run.');
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        newUrls.push(url);
        objectUrls.current.add(url);
      }
      if (!alive.current) return;
      setSessions(previous => [{
        result: analysis, urls: newUrls, model, files: [...files], sampleIds: [...sampleIds],
      }, ...previous]);
      setActiveId(analysis.survey_id);
      setImageIndex(0);
      setSelected(analysis.images[0]?.detections[0]?.id || null);
    } catch (err) {
      newUrls.forEach(url => { URL.revokeObjectURL(url); objectUrls.current.delete(url); });
      if (!controller.signal.aborted && alive.current) setError(err instanceof Error ? err.message : 'Survey analysis failed.');
    } finally {
      if (alive.current) setBusy(false);
      requestController.current = null;
    }
  }

  function openSession(item: Session) {
    setActiveId(item.result.survey_id);
    setModel(item.model);
    setProfile(item.result.profile);
    setTta(item.result.tta);
    setBudget(item.result.operating.budget);
    setFiles(item.files);
    setSampleIds(item.sampleIds);
    setImageIndex(0);
    setSelected(item.result.images[0]?.detections[0]?.id || null);
    setError('');
  }

  function newSurvey() {
    setActiveId(null);
    setFiles([]);
    setSampleIds([]);
    setSelected(null);
    setImageIndex(0);
    setError('');
    fileInput.current?.focus();
  }

  const commands: Command[] = [
    ...samples.map(sample => ({
      id: `sample-${sample.id}`,
      title: `Open sample · ${sample.name}`,
      detail: `${sample.dataset} / held-out test image`,
      run: () => {
        setActiveId(null); setFiles([]); setSampleIds([sample.id]); setSelected(null); setError('');
      },
    })),
    ...(['general', 'ghost-gear'] as const).map(key => ({
      id: `model-${key}`, title: key === 'general' ? 'Model · General v0.4' : 'Model · Ghost-gear specialist',
      detail: 'Applies to the next analysis', run: () => setModel(key),
    })),
    ...[0.25, 0.5, 1, 2, 3].map(value => ({
      id: `budget-${value}`, title: `Budget · ${value} false alarms / image`,
      detail: 'Instant operating-point preview; re-run to save', run: () => setBudget(value),
    })),
    { id: 'new', title: 'New survey', detail: 'Clear the current input selection', run: newSurvey },
    ...(result ? [
      { id: 'json', title: 'Export · evidence pack JSON', detail: 'Saved run, not local slider preview', run: () => { window.location.href = result.packs.json; } },
      { id: 'html', title: 'Open · HTML report', detail: 'Saved evidence and provenance', run: () => { window.open(result.packs.html, '_blank', 'noopener,noreferrer'); } },
    ] : []),
  ];

  function changeSort(key: 'probability' | 'raw_score') {
    if (sort === key) setDescending(value => !value);
    else { setSort(key); setDescending(true); }
  }

  return (
    <div className="ns-dashboard" ref={root}>
      <a href="#ns-workspace" className="ns-skip">Skip to survey viewer</a>
      <header className="ns-header">
        <div className="ns-brand-group">
          <a href="/" className="ns-brand" aria-label="NetSight home"><span aria-hidden="true">⌁</span> NetSight<span className="ns-brand-dot" /></a>
          <span className="ns-header-divider" />
          <span className="ns-workspace-title">Research workspace <span>v0.4</span></span>
        </div>
        <div className="ns-header-actions">
          <span className="ns-device"><i className={health ? 'online' : ''} />{health?.device.toUpperCase() || (connecting ? 'CONNECTING' : 'OFFLINE')}</span>
          {result && <span className="ns-latency">{(result.timing_ms / 1000).toFixed(2)} s</span>}
          <button className="ns-command-trigger" onClick={() => setPalette(true)} aria-label="Open command palette">⌕ <span>Commands</span><kbd>⌘ / Ctrl K</kbd></button>
        </div>
      </header>

      {(connectionError || error) && (
        <div className="ns-error" role="alert">
          <div><strong>{connectionError ? 'Local API unavailable' : 'Could not complete that action'}</strong><p>{error || connectionError}</p>
            {connectionError && <><code>{START}</code><p>Start from the repository root, then retry. Initial model loading can take a moment.</p></>}
          </div>
          {connectionError ? <button onClick={() => void connect()} disabled={connecting}>{connecting ? 'Connecting…' : 'Retry connection'}</button> :
            <button onClick={() => setError('')} aria-label="Dismiss error">×</button>}
        </div>
      )}

      <div className="ns-layout">
        <aside className="ns-rail" aria-label="Surveys and inputs">
          <div className="ns-panel-heading"><h2>Surveys</h2><button onClick={newSurvey} disabled={busy} aria-label="Start a new survey">+</button></div>
          <div className="ns-survey-list">
            {!sessions.length && <p className="ns-micro">Your surveys stay in this workspace until the page is closed. Evidence packs remain on the API host.</p>}
            {sessions.map((item, i) => (
              <button key={item.result.survey_id} className={`ns-survey-item ${activeId === item.result.survey_id ? 'active' : ''}`}
                onClick={() => openSession(item)} disabled={busy}>
                <span className="ns-survey-icon" aria-hidden="true">▧</span>
                <span><strong>Survey {String(sessions.length - i).padStart(2, '0')}</strong>
                  <small>{item.result.images.length} images · {item.result.operating.flagged} flagged</small></span>
                <i className={`ns-level-dot ${item.result.claim.level}`} />
              </button>
            ))}
          </div>

          <div className="ns-section-title"><h3>Survey inputs</h3><span>{files.length + sampleIds.length}/20</span></div>
          <label className={`ns-dropzone ${dragOver ? 'drag-over' : ''} ${busy ? 'disabled' : ''}`}
            onDragOver={event => { event.preventDefault(); if (!busy) setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={event => { event.preventDefault(); setDragOver(false); if (!busy) addFiles(Array.from(event.dataTransfer.files)); }}>
            <input ref={fileInput} type="file" multiple accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp"
              disabled={busy} aria-label="Upload sonar images"
              onChange={event => { addFiles(Array.from(event.target.files || [])); event.target.value = ''; }} />
            <span className="ns-upload-icon" aria-hidden="true">↑</span>
            <strong>Drop sonar images</strong><span>or choose files</span>
            <small>PNG, JPG, TIFF, BMP · 50 MB total<br />Multiple images = one survey</small>
          </label>
          {!!files.length && <ul className="ns-file-list">{files.map((file, i) => (
            <li key={`${file.name}-${i}`}><span title={file.name}>{file.name}</span>
              <button disabled={busy} aria-label={`Remove ${file.name}`} onClick={() => setFiles(values => values.filter((_, n) => n !== i))}>×</button></li>
          ))}</ul>}

          <div className="ns-section-title"><h3>Try held-out samples</h3><span>TEST</span></div>
          <p className="ns-micro">Choose one or more. These are test-set images, not calibration inputs.</p>
          <div className="ns-sample-grid" aria-busy={connecting}>
            {connecting && !samples.length && Array.from({ length: 4 }, (_, i) => <div key={i} className="ns-sample-skeleton" />)}
            {samples.map(sample => (
              <button key={sample.id} className={`ns-sample ${sampleIds.includes(sample.id) ? 'chosen' : ''}`}
                onClick={() => toggleSample(sample.id)} disabled={busy}
                aria-pressed={sampleIds.includes(sample.id)} aria-label={`${sample.name}, ${sample.dataset}, held-out test set`}>
                <img src={sample.url} alt="" loading="lazy" />
                <span className="ns-sample-check" aria-hidden="true">{sampleIds.includes(sample.id) ? '✓' : '+'}</span>
                <strong>{sample.dataset}</strong><small title={sample.name}>{sample.name}</small>
              </button>
            ))}
          </div>
          {!connecting && !samples.length && !connectionError && <p className="ns-micro">No held-out samples are available. Upload a local image to begin.</p>}
          <div className="ns-rail-footer"><span className="ns-live-dot" /> LOCAL PROCESSING<span>Images stay on the API host.</span></div>
        </aside>

        <main className="ns-centre" id="ns-workspace" tabIndex={-1}>
          <div className="ns-survey-heading">
            <div><p className="ns-eyebrow">DETECTION / SURVEY REVIEW</p>
              <h1>{result ? `Survey ${result.survey_id.slice(0, 8)}` : 'See what’s beneath.'}</h1>
              <span className="ns-model-chip">{/research/i.test(modelClass) ? 'RESEARCH MODEL — not for product use' : `${modelClass} — human review required`}</span>
              {result && <p className="ns-model-label">{result.model.label}</p>}
            </div>
            <div className="ns-exports">
              <a href={result?.packs.json} aria-disabled={!result} tabIndex={result ? 0 : -1}>↓ <span>Download evidence pack (JSON)</span></a>
              <a href={result?.packs.html} aria-disabled={!result} tabIndex={result ? 0 : -1} target="_blank" rel="noreferrer">HTML report ↗</a>
            </div>
          </div>

          <section className="ns-controls" aria-label="Analysis controls">
            <label>Model<select value={model} onChange={event => setModel(event.target.value as ModelKey)} disabled={busy}>
              <option value="general">General v0.4</option><option value="ghost-gear">Ghost-gear specialist</option>
            </select></label>
            <label>Applicability profile<select value={profile} onChange={event => setProfile(event.target.value as Profile)} disabled={busy}>
              {profiles.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select></label>
            <label className="ns-budget">False alarms / image <output>{budget.toFixed(2)}</output>
              <input type="range" min="0.25" max="3" step="0.25" value={budget}
                onChange={event => setBudget(Number(event.target.value))} disabled={busy}
                aria-label="False-alarm budget per image" aria-valuetext={`${budget} false alarms per image`} />
              <span><small>0.25 · cautious</small><small>3 · exploratory</small></span>
            </label>
            <label className="ns-tta"><input type="checkbox" checked={tta} onChange={event => setTta(event.target.checked)} disabled={busy} />
              <span>Flip TTA<small>More views</small></span></label>
            <label className="ns-tta"><input type="checkbox" checked={showAll} onChange={event => setShowAll(event.target.checked)} disabled={busy} />
              <span>Show all candidates<small>Include near-zero boxes</small></span></label>
            <button className="ns-run" disabled={busy || !health || !files.length && !sampleIds.length} onClick={() => void runSurvey()}>
              {busy ? 'Analyzing…' : result ? 'Re-run survey ↗' : 'Analyze survey ↗'}
            </button>
          </section>

          {(localBudget || staleControls) && result && (
            <div className="ns-preview-note" role="status">
              {localBudget ? `Local budget preview · saved run uses ${result.operating.budget.toFixed(2)} FA/image. ` : ''}
              {staleControls ? 'Model, profile or TTA changes apply on the next run. ' : ''}
              Re-run to update evidence, claim, validation recall and downloads.
            </div>
          )}

          <section className="ns-stage" aria-label="Survey imagery">
            {busy ? <Running /> : image && session && preview ? (
              <Viewer image={image} url={session.urls[imageIndex]} flags={preview.flags}
                selected={selected} onSelect={chooseContact} zoomRequest={zoomRequest} />
            ) : (
              <div className="ns-empty">
                <div className="ns-empty-target" aria-hidden="true"><span /><i /><b>⌁</b></div>
                <p className="ns-eyebrow">YOUR NEXT SURVEY STARTS HERE</p>
                <h2>From sonar returns<br />to reviewable evidence.</h2>
                <p>Upload a side-scan image, or choose held-out samples.<br />NetSight proposes contacts. Your team makes the call.</p>
                <button onClick={() => fileInput.current?.click()} disabled={busy}>Choose sonar images <span>↗</span></button>
                <div className="ns-empty-steps"><span><b>01</b> Load a survey</span><span><b>02</b> Set your budget</span><span><b>03</b> Review & export</span></div>
              </div>
            )}
          </section>

          {result && !busy && session && (
            <div className="ns-thumbnails" aria-label="Survey images">
              {result.images.map(img => (
                <button key={img.index} onClick={() => {
                  setImageIndex(img.index); setSelected(img.detections[0]?.id || null);
                }} className={imageIndex === img.index ? 'active' : ''} aria-pressed={imageIndex === img.index}>
                  <img src={session.urls[img.index]} alt="" /><span>{String(img.index + 1).padStart(2, '0')}<small>{img.name}</small></span>
                </button>
              ))}
            </div>
          )}
          <footer className="ns-workspace-footer">
            <span>⌁ NETSIGHT / RESEARCH DETECTOR</span>
            <span><kbd>j</kbd><kbd>k</kbd> contacts <kbd>↵</kbd> zoom <kbd>0</kbd> fit · wheel + drag</span>
          </footer>
        </main>

        <aside className="ns-inspector" aria-label="Evidence inspector">
          <div className="ns-panel-heading"><h2>Evidence inspector</h2><span className="ns-micro">LIVE REVIEW</span></div>
          {!result ? (
            <div className="ns-inspector-empty">
              <span aria-hidden="true">◎</span><h3>Context before confidence.</h3>
              <p>After analysis, inspect applicability, validation recall, and the evidence behind each flagged contact.</p>
              <div><b>01 / Applicability</b><p>Does this survey resemble the reference geometry?</p></div>
              <div><b>02 / Operating point</b><p>A label-free count budget, not an object-count prediction.</p></div>
              <div><b>03 / Contact evidence</b><p>Calibrated probability and measurable image features.</p></div>
            </div>
          ) : (
            <>
              <section className="ns-claim">
                <div className="ns-section-title"><h3>Applicability</h3><span className={`ns-claim-badge ${result.claim.level}`}>
                  {result.claim.level === 'calibrated' ? '+' : result.claim.level === 'indicative' ? '~' : '×'} {result.claim.level}
                </span></div>
                <p>{result.claim.statement}</p>
                {!!result.claim.reasons.length && <details open><summary>Why this level?</summary><ul>{result.claim.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul></details>}
                {(localBudget || staleControls) && <p className="ns-micro">Applicability shown for the saved run.</p>}
              </section>
              <section className="ns-operating">
                <div className="ns-section-title"><h3>Operating summary</h3><span>{localBudget ? 'PREVIEW' : 'SAVED RUN'}</span></div>
                <div className="ns-stat-grid">
                  <div><span>Flagged contacts</span><strong>{preview?.flags.size ?? 0}<small> / {allContacts.length}</small></strong></div>
                  <div><span>Budget / image</span><strong>{budget.toFixed(2)}</strong></div>
                </div>
                <dl className="ns-summary-list">
                  <div><dt>Raw-score threshold</dt><dd>{preview?.threshold == null ? '∞ · no flags' : preview.threshold.toFixed(4)}</dd></div>
                  <div><dt>Validation recall{localBudget ? ' · saved budget' : ''}</dt><dd>{percent(result.operating.recall)}</dd></div>
                  <div><dt>Recall interval</dt><dd>{percent(result.operating.recall_ci[0])}–{percent(result.operating.recall_ci[1])}</dd></div>
                </dl>
                <p className="ns-micro">Recall: {result.operating.recall_source}. {localBudget && 'Re-run for a recall estimate at the preview budget.'}</p>
                <p className="ns-micro">Count rule: top floor(budget × images) by raw score; boundary ties are included. The budget is not a measured false-alarm rate for this survey.</p>
              </section>
              <section className="ns-contact-section">
                <div className="ns-section-title"><h3>Selected contact</h3>
                  {contact && <button onClick={() => setZoomRequest(n => n + 1)}>Zoom ↗</button>}
                </div>
                {contact ? (
                  <div ref={contactCard} className="ns-contact-card">
                    <div className="ns-contact-title"><strong>{contact.id}</strong><span className={preview?.flags.has(contact.id) ? 'ns-flagged-label' : 'ns-muted'}>{preview?.flags.has(contact.id) ? '● Flagged' : '○ Below threshold'}</span></div>
                    <div className="ns-probability">
                      <div className="ns-gauge" role="meter" aria-label="Calibrated probability" aria-valuemin={0} aria-valuemax={100}
                        aria-valuenow={contact.probability * 100}
                        style={{ background: `conic-gradient(#6de2c3 ${contact.probability * 360}deg, #18303b 0)` }}>
                        <span>{percent(contact.probability)}</span>
                      </div><div><strong>Contact probability</strong><p>Calibrated on<br />validation surveys</p></div>
                    </div>
                    <dl className="ns-summary-list">
                      <div><dt>Raw score</dt><dd>{contact.raw_score.toFixed(4)}</dd></div>
                      <div><dt>Box size</dt><dd>{Math.round(contact.box[2] - contact.box[0])} × {Math.round(contact.box[3] - contact.box[1])} px</dd></div>
                      <div><dt>Image</dt><dd title={contact.imageName}>{contact.imageIndex + 1} / {result.images.length}</dd></div>
                    </dl>
                    <Evidence contact={contact} />
                  </div>
                ) : <p className="ns-muted">Select a box or contact below to inspect its evidence.</p>}
              </section>
              <section className="ns-contacts">
                <div className="ns-section-title"><h3>All contacts</h3><span>{contacts.length}</span></div>
                {!contacts.length ? <p className="ns-muted">No contacts were returned. A clear image is not evidence of absence; try another survey or review the source image.</p> : (
                  <table>
                    <caption className="ns-sr-only">Contacts across every image. Select a row; j and k move selection.</caption>
                    <thead><tr><th scope="col">Contact</th>
                      <th scope="col" aria-sort={sort === 'probability' ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => changeSort('probability')}>Prob. {sort === 'probability' ? descending ? '↓' : '↑' : '↕'}</button></th>
                      <th scope="col" aria-sort={sort === 'raw_score' ? descending ? 'descending' : 'ascending' : 'none'}><button onClick={() => changeSort('raw_score')}>Raw {sort === 'raw_score' ? descending ? '↓' : '↑' : '↕'}</button></th></tr></thead>
                    <tbody>{contacts.map(item => (
                      <tr key={item.id} className={selected === item.id ? 'active' : ''}>
                        <td><button onClick={() => chooseContact(item.id)} aria-pressed={selected === item.id}
                          onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); chooseContact(item.id); setZoomRequest(n => n + 1); } }}>
                          <span className={preview?.flags.has(item.id) ? 'ns-table-flag flagged' : 'ns-table-flag'} aria-label={preview?.flags.has(item.id) ? 'Flagged' : 'Below threshold'} />
                          {item.id}<small> / {String(item.imageIndex + 1).padStart(2, '0')}</small>
                        </button></td><td>{percent(item.probability)}</td><td>{item.raw_score.toFixed(3)}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                )}
              </section>
            </>
          )}
        </aside>
      </div>
      {palette && <CommandPalette commands={commands} close={() => setPalette(false)} />}
    </div>
  );
}
