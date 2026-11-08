import { Composition } from 'remotion';
import { Explainer } from './Explainer';

export function RemotionRoot() {
  return (
    <Composition
      id="Explainer"
      component={Explainer}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={600}
    />
  );
}
