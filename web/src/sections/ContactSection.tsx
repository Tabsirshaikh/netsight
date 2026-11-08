import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function ContactSection() {
  const c = partC.contact;
  return (
    <StoryFrame {...c} className="c-contact">
      <p className="c-status c-reveal">{c.label}</p>
      <ol className="c-journey">
        {c.journey.map(item => (
          <li className="c-reveal" key={item.title}>
            <span className="c-journey-node" aria-hidden="true" />
            <h3>{item.title}</h3><p>{item.body}</p>
          </li>
        ))}
      </ol>
      <div className="c-pack c-reveal">
        <div>
          <h3>{c.packTitle}</h3>
          <p>{c.packIntro}</p>
          <p className="c-footnote">{c.ledgerNote}</p>
          <p className="c-source">{c.ledgerSource}</p>
        </div>
        <ul>{c.pack.map(field => <li key={field}>{field}</li>)}</ul>
      </div>
      <div className="c-evidence-block c-reveal">
        <h3>{c.matrixTitle}</h3>
        <p className="c-footnote">{c.matrixNote}</p>
        <div className="c-table-wrap">
          <table>
            <thead><tr>{c.matrixHeaders.map(header => <th scope="col" key={header}>{header}</th>)}</tr></thead>
            <tbody>
              {c.matrix.map(row => (
                <tr key={row[0]}><th scope="row">{row[0]}</th><td className="c-numeric">{row[1]}</td><td>{row[2]}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </StoryFrame>
  );
}
