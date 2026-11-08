import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function CompletenessSection() {
  const c = partC.completeness;
  return (
    <StoryFrame {...c} className="c-completeness" pin>
      <div className="c-map-layout">
        <figure className="c-map-panel">
          <figcaption>
            <h3>{c.mapTitle}</h3>
            <p className="c-status">{partC.common.design}</p>
          </figcaption>
          <svg viewBox="0 0 660 400" role="img" aria-label={c.mapLabel}>
            <defs>
              <pattern id="partc-grid" width="30" height="30" patternUnits="userSpaceOnUse">
                <path d="M30 0H0V30" fill="none" stroke="#6de2c3" strokeOpacity=".12" />
              </pattern>
              <pattern id="partc-gap" width="9" height="9" patternUnits="userSpaceOnUse">
                <path d="M0 9L9 0" stroke="#f2ac7e" strokeOpacity=".55" />
              </pattern>
            </defs>
            <rect x="15" y="15" width="630" height="370" rx="8" fill="#061d28" />
            <rect x="15" y="15" width="630" height="370" fill="url(#partc-grid)" />
            {[65, 175, 285, 395, 505].map((x, i) => (
              <g key={x}>
                <rect className="c-swath" x={x - 30} y="35" width="100" height="330" fill="#6de2c3" opacity=".18" />
                <path
                  className="c-draw"
                  d={i % 2 === 0 ? `M${x + 20} 40V360` : `M${x + 20} 360V40`}
                  stroke="#91dfd1" strokeWidth="2" strokeDasharray="6 7" fill="none"
                />
              </g>
            ))}
            <g className="c-gap">
              <path d="M205 35H235V365H205Z" fill="#031019" stroke="#f2ac7e" />
              <path d="M205 35H235V365H205Z" fill="url(#partc-gap)" />
            </g>
            <g className="c-gap">
              <path d="M365 150H465V235H365Z" fill="#ba8951" opacity=".4" />
              <path d="M365 150H465V235H365Z" stroke="#f2ac7e" fill="none" strokeDasharray="5 5" />
            </g>
            <g className="c-gap">
              <path d="M575 35H625V365H575Z" fill="#031019" stroke="#f2ac7e" />
              <path d="M575 35H625V365H575Z" fill="url(#partc-gap)" />
            </g>
          </svg>
          <ul className="c-map-legend">
            {c.legend.map((item, i) => (
              <li key={item}><span className={`c-map-key c-map-key-${i}`} aria-hidden="true" />{item}</li>
            ))}
          </ul>
          <p className="c-source">{c.footer}</p>
        </figure>
        <div className="c-map-notes">
          {c.notes.map(note => (
            <article className="c-reveal" key={note.title}>
              <h3>{note.title}</h3><p>{note.body}</p>
            </article>
          ))}
        </div>
      </div>
    </StoryFrame>
  );
}
