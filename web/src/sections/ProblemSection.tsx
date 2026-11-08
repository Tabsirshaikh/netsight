import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function ProblemSection() {
  const c = partC.problem;
  return (
    <StoryFrame {...c} className="c-problem">
      <div className="c-stat-grid">
        {c.stats.map(stat => (
          <article className="c-stat c-reveal" key={stat.title}>
            <strong>{stat.value}</strong>
            <h3>{stat.title}</h3>
            <p>{stat.detail}</p>
            <p className="c-source">{stat.source}</p>
          </article>
        ))}
      </div>
      <div className="c-workflow c-reveal">
        <h3>{c.workflowTitle}</h3>
        <ol>
          {c.workflow.map(item => <li key={item}>{item}</li>)}
        </ol>
        <p className="c-source">{c.workflowSource}</p>
      </div>
      <aside className="c-callout c-reveal">
        <p className="c-lead">{c.suspects}</p>
        <p>{c.interpretation}</p>
        <p className="c-source">{c.studySource}</p>
      </aside>
      <p className="c-closing c-reveal">{c.bridge}</p>
    </StoryFrame>
  );
}
