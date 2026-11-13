import type { Reliability } from './types';

const COLOURS: Record<string, string> = {
  'NetSight (beta)': '#6de2c3',
  'B1 temperature': '#e3b55b',
  'B0 raw score': '#8a97a6',
};

/** Held-out reliability: shown P(real) against the observed real rate, with 95% intervals. */
export function ReliabilityChart({ reliability }: { reliability: Reliability }) {
  const size = 240;
  const pad = 30;
  const plot = size - pad - 8;
  const x = (p: number) => pad + p * plot;
  const y = (r: number) => 8 + (1 - r) * plot;
  const methods = Object.entries(reliability.methods);
  return (
    <section className="ns-operating" aria-label="Reliability on held-out surveys">
      <div className="ns-section-title"><h3>Reliability</h3><span>HELD-OUT</span></div>
      <svg viewBox={`0 0 ${size} ${size + 14}`} width="100%" role="img"
        aria-label={`Reliability diagram. ${methods.map(([n, m]) => `${n} ECE ${m.ece.toFixed(3)}`).join('; ')}`}
        style={{ color: 'currentColor', fontSize: 9 }}>
        <rect x={pad} y={8} width={plot} height={plot} fill="none" stroke="currentColor" strokeOpacity={0.3} />
        <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="currentColor" strokeOpacity={0.4} strokeDasharray="4 3" />
        {[0, 0.5, 1].map(t => (
          <g key={t}>
            <text x={x(t)} y={y(0) + 12} textAnchor="middle" fill="currentColor">{t}</text>
            <text x={pad - 4} y={y(t) + 3} textAnchor="end" fill="currentColor">{t}</text>
          </g>
        ))}
        <text x={x(0.5)} y={size + 12} textAnchor="middle" fill="currentColor">Shown P(real)</text>
        {methods.map(([name, m]) => {
          const colour = COLOURS[name] ?? 'currentColor';
          return (
            <g key={name}>
              {m.bins.map((b, i) => (
                <line key={i} x1={x(b.mean_predicted)} x2={x(b.mean_predicted)} y1={y(b.ci_low)} y2={y(b.ci_high)}
                  stroke={colour} strokeOpacity={0.45} />
              ))}
              <polyline fill="none" stroke={colour} strokeWidth={2}
                points={m.bins.map(b => `${x(b.mean_predicted).toFixed(1)},${y(b.observed_rate).toFixed(1)}`).join(' ')} />
            </g>
          );
        })}
      </svg>
      <dl className="ns-summary-list">
        {methods.map(([name, m]) => (
          <div key={name}><dt><span style={{ color: COLOURS[name] }}>■</span> {name}</dt><dd>ECE {m.ece.toFixed(3)}</dd></div>
        ))}
      </dl>
      <p className="ns-micro">{reliability.n_test.toLocaleString()} detections ({reliability.positives_test.toLocaleString()} real) from test surveys never used for training or calibration. On the dashed line, shown P(real) matches how often contacts were real.</p>
    </section>
  );
}
