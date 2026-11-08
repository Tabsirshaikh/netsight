import { StoryFrame } from '../components/StoryFrame';
import { partC } from '../content.partC';

export function EightStagesSection() {
  const c = partC.pipeline;
  return (
    <StoryFrame {...c} className="c-pipeline">
      <p className="c-status c-reveal">{partC.common.architecture}</p>
      <div className="c-chain-terminal c-reveal">{c.input}</div>
      <ol className="c-stage-grid">
        {c.stages.map(stage => (
          <li className="c-layer" key={stage.id}>
            <span className="c-stage-number">{stage.id}</span>
            <div>
              <h3>{stage.name}</h3>
              <p className="c-output">{stage.output}</p>
              <p>{stage.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <div className="c-chain-terminal c-reveal">{c.output}</div>
      <p className="c-source c-reveal">{c.footer}</p>
    </StoryFrame>
  );
}
