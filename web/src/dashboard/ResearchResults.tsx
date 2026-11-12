import { useEffect, useState } from 'react';
import type { Analysis, Completeness, VerificationPlan } from './types';
import { api, cellDescription, completenessColor, percent } from './types';

export function CompletenessResults({ completeness, result, imageIndex, onImage }: {
  completeness: Completeness;
  result: Analysis;
  imageIndex: number;
  onImage: (index: number) => void;
}) {
  if (!completeness.available) {
    return (
      <section className="ns-completeness">
        <div className="ns-section-title"><h3>Search completeness</h3></div>
        <p className="ns-muted">{completeness.reason}</p>
      </section>
    );
  }
  const c = completeness;
  return (
    <section className="ns-completeness">
      <div className="ns-section-title">
        <h3>Search completeness</h3>
        <span className={`ns-claim-badge ${c.claim_level}`}>{c.claim_level}</span>
      </div>
      <p className={c.claim_level === 'calibrated' ? 'ns-micro ns-verbatim' : 'ns-preview-note ns-verbatim'}>{c.caveat}</p>
      <dl className="ns-summary-list">
        <div><dt>Overall Pd{c.claim_level !== 'calibrated' ? ' · indicative' : ''}</dt><dd>{percent(c.pd)}</dd></div>
        <div><dt>90% lower bound</dt><dd>{percent(c.pd_lower90)}</dd></div>
        <div><dt>Injected targets found</dt><dd>{c.detected} / {c.trials}</dd></div>
        <div><dt>Target library size</dt><dd>{c.library_size}</dd></div>
        <div><dt>Profile</dt><dd>{c.profile}</dd></div>
        <div><dt>Cells with enough trials</dt><dd>{c.cells_ok}</dd></div>
      </dl>
      <p className="ns-micro ns-verbatim">Method: {c.method}</p>
      <p className="ns-micro">Measured using real labelled objects from validation surveys of the selected applicability profile, injected into this survey’s own images. Saved run, not the local budget preview.</p>
      <p className="ns-micro">Cell colour: 90% lower bound, warm = low, teal = high. Hatched = too few trials. Focus a cell for its measurements; activate it to select the image.</p>
      <div className="ns-completeness-images">
        {result.images.map(image => (
          <div key={image.index}>
            <button className="ns-grid-image" aria-pressed={imageIndex === image.index} onClick={() => onImage(image.index)}>
              {image.index + 1}. {image.name}
            </button>
            <div className="ns-completeness-grid" style={{ gridTemplateColumns: `repeat(${c.grid[1]}, minmax(0, 1fr))` }}>
              {Array.from({ length: c.grid[0] * c.grid[1] }, (_, i) => {
                const row = Math.floor(i / c.grid[1]);
                const col = i % c.grid[1];
                const cell = c.cells.find(item => item.image_index === image.index && item.row === row && item.col === col);
                const label = `Image ${image.index + 1}, row ${row + 1}, column ${col + 1}: ${cell ? cellDescription(cell) : 'not measured'}`;
                return (
                  <button key={i} onClick={() => onImage(image.index)} title={label} aria-label={label}
                    className={cell?.status === 'insufficient_trials' ? 'ns-insufficient' : ''}
                    style={{ backgroundColor: cell ? completenessColor(cell.pd_lower) : 'var(--ns-raised)' }}>
                    <span className="ns-sr-only">{label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function PlanResults({ url, onSelect }: { url: string; onSelect: (id: string) => void }) {
  const [state, setState] = useState<{ url: string; plan?: VerificationPlan; error?: string }>({ url });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ url });
    void api<VerificationPlan>(url, { signal: controller.signal }).then(
      plan => { if (!controller.signal.aborted) setState({ url, plan }); },
      error => {
        if (!controller.signal.aborted) setState({ url, error: error instanceof Error ? error.message : 'Could not load verification plan.' });
      },
    );
    return () => controller.abort();
  }, [url, retry]);

  const plan = state.url === url ? state.plan : undefined;
  const error = state.url === url ? state.error : undefined;
  return (
    <section className="ns-plan">
      <div className="ns-section-title"><h3>Verification plan</h3><span>SAVED RUN</span></div>
      {error ? <div role="alert"><p className="ns-muted">Verification plan could not be loaded: {error}</p><button onClick={() => setRetry(n => n + 1)}>Retry plan</button></div> :
        !plan ? <p className="ns-muted" role="status">Loading verification plan…</p> : (
          <>
            <p className="ns-micro ns-verbatim">{plan.note}</p>
            <dl className="ns-summary-list">
              <div><dt>Expected real total</dt><dd>{plan.expected_real_total.toFixed(2)}</dd></div>
              <div><dt>Excluded · withdrawn</dt><dd>{plan.excluded_withdrawn}</dd></div>
              <div><dt>Excluded · no position</dt><dd>{plan.excluded_no_position}</dd></div>
            </dl>
            {plan.entries.length ? (
              <div className="ns-plan-table">
                <table>
                  <caption>Top 10 verification entries</caption>
                  <thead><tr><th scope="col">Rank / contact</th><th scope="col">P(real)</th><th scope="col">Cumulative expected real finds</th></tr></thead>
                  <tbody>{[...plan.entries].sort((a, b) => a.rank - b.rank).slice(0, 10).map(entry => (
                    <tr key={entry.contact_id}>
                      <td><button onClick={() => onSelect(entry.contact_id)}>{entry.rank}. {entry.contact_id}</button></td>
                      <td>{percent(entry.p_real)}</td><td>{entry.cumulative_expected_real.toFixed(2)}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : <p className="ns-muted">No contacts eligible for this verification plan.</p>}
          </>
        )}
    </section>
  );
}
