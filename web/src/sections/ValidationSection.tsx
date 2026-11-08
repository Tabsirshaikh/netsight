import { content } from '../content';
import { partC } from '../content.partC';
import { StoryFrame } from '../components/StoryFrame';

export function ValidationSection() {
  const c = partC.validation;
  const trust = content.s06;
  return (
    <StoryFrame {...c} className="c-validation">
      <p className="c-status c-reveal">{partC.common.measured}</p>

      <div className="c-evidence-block">
        <h3 className="c-reveal">{c.splitTitle}</h3>
        <div className="c-split-grid">
          {content.s04.columns.map(column => (
            <article className={`c-split c-reveal ${column.tone}`} key={column.title}>
              <p className="c-kicker">{column.label}</p>
              <strong>{column.value.toFixed(2)}</strong>
              <div className="c-meter" aria-hidden="true">
                <span style={{ transform: `scaleX(${column.value})` }} />
              </div>
              <h4>{column.title}</h4>
              <p>{column.caption}</p>
            </article>
          ))}
        </div>
        <p className="c-footnote">{c.splitNote}</p>
        <p className="c-source">{partC.common.measuredSource}</p>
      </div>

      <div className="c-evidence-block c-reveal">
        <h3>{c.resultsTitle}</h3>
        <div className="c-table-wrap">
          <table>
            <thead><tr><th scope="col">{c.dataset}</th><th scope="col">{c.target}</th><th scope="col">{c.metric}</th></tr></thead>
            <tbody>
              {content.s05.results.map(result => (
                <tr key={result.dataset}>
                  <th scope="row">{result.dataset}</th>
                  <td>{result.target}</td>
                  <td className="c-numeric">{result.value.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="c-result-summary">
          <p><span>{c.average}</span><strong>{content.s05.average.toFixed(2)}</strong><small>{partC.common.ap50}</small></p>
          <p><span>{c.compared}</span><strong>{content.s05.previousAverage.toFixed(2)}</strong><small>{partC.common.ap50}</small></p>
        </div>
        <p>{content.s05.intro}</p>
        <p>{content.s05.specialist}</p>
        <p className="c-source">{partC.common.measuredSource}</p>
      </div>

      <div className="c-trust-grid">
        <div className="c-card c-reveal">
          <h3>{c.calibrationTitle}</h3>
          <p className="c-kicker">{c.calibrationMetric}</p>
          <strong className="c-error">{trust.calibrationError[0].toFixed(3)}–{trust.calibrationError[1].toFixed(3)}</strong>
          <p>{c.calibrationNote}</p>
          <h4>{c.levelsTitle}</h4>
          <dl className="c-levels">
            {trust.levels.map(level => (
              <div key={level.name}><dt>{level.name}</dt><dd>{level.text}</dd></div>
            ))}
          </dl>
          <p className="c-source">{partC.common.measuredSource}</p>
        </div>
        <div className="c-card c-reveal">
          <h3>{c.budgetTitle}</h3>
          {[
            { title: c.fixed, held: trust.budget.fixedHeld },
            { title: c.counting, held: trust.budget.labelFreeHeld }
          ].map(row => (
            <div className="c-budget-row" key={row.title}>
              <p>{row.title}<strong>{row.held} / {trust.budget.surveys}</strong></p>
              <div className="c-tally" aria-hidden="true">
                {Array.from({ length: trust.budget.surveys }, (_, i) => (
                  <span className={i < row.held ? 'is-held' : ''} key={i} />
                ))}
              </div>
            </div>
          ))}
          <p>{trust.budgetText}</p>
          <p className="c-footnote">{c.budgetNote}</p>
          <p className="c-source">{partC.common.measuredSource}</p>
        </div>
      </div>

      <div className="c-evidence-block c-reveal">
        <h3>{c.learningTitle}</h3>
        <p className="c-kicker">{c.learningMetric}</p>
        <ul className="c-learning">
          {content.s08.points.map(point => (
            <li key={point.recordings}><strong>{point.recordings}</strong><span aria-hidden="true">→</span><strong>{point.value.toFixed(2)}</strong></li>
          ))}
        </ul>
        <p className="c-source">{partC.common.measuredSource}</p>
      </div>
      <aside className="c-limits c-reveal">
        <h3>{c.limitsTitle}</h3>
        <ul>{c.limits.map(limit => <li key={limit}>{limit}</li>)}</ul>
      </aside>
    </StoryFrame>
  );
}
