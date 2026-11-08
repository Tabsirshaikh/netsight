import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function QuestionsSection() {
  const c = partC.questions;
  return (
    <StoryFrame {...c} className="c-questions">
      <div className="c-pillars">
        {c.pillars.map(pillar => (
          <article className="c-card c-reveal" key={pillar.name}>
            <p className="c-kicker">{pillar.question}</p>
            <h3>{pillar.name}</h3>
            <p>{pillar.body}</p>
            <p className="c-status">{pillar.status}</p>
          </article>
        ))}
      </div>
      <div className="c-preparation">
        <h3 className="c-reveal">{c.preparationTitle}</h3>
        <div className="c-preparation-grid">
          {c.preparation.map(item => (
            <article className="c-reveal" key={item.title}>
              <h4>{item.title}</h4>
              <p>{item.body}</p>
              <p className="c-status">{item.status}</p>
            </article>
          ))}
        </div>
      </div>
      <p className="c-footnote c-reveal">{c.footer}</p>
    </StoryFrame>
  );
}
