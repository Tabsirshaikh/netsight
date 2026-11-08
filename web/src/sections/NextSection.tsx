import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function NextSection() {
  const c = partC.next;
  const briefHref = `data:text/plain;charset=utf-8,${encodeURIComponent(c.brief)}`;
  return (
    <StoryFrame {...c} className="c-next">
      <div className="c-boundary-grid">
        <article className="c-card c-reveal">
          <p className="c-kicker">{partC.common.measured}</p>
          <h3>{c.measuredTitle}</h3><p>{c.measuredBody}</p>
        </article>
        <article className="c-card c-reveal">
          <p className="c-kicker">{partC.common.design}</p>
          <h3>{c.designTitle}</h3><p>{c.designBody}</p>
        </article>
      </div>
      <div className="c-pilot c-reveal">
        <h3>{c.requestTitle}</h3>
        <ul>{c.requests.map(request => <li key={request}>{request}</li>)}</ul>
        <p className="c-footnote">{c.dataNote}</p>
      </div>
      <div className="c-actions c-reveal">
        <a className="c-button" href={briefHref} download={c.downloadName}>{c.briefAction}<span aria-hidden="true">↘</span></a>
        <a className="c-text-link" href="#honest-test">{c.reviewAction}<span aria-hidden="true">↗</span></a>
      </div>
      <footer className="c-footer">
        <p>{c.footer}</p>
        <a href="#mission">{c.top}<span aria-hidden="true">↑</span></a>
      </footer>
    </StoryFrame>
  );
}
