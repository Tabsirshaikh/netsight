import { Suspense, useRef, useState } from 'react';
import { Canvas } from '@react-three/fiber';
import { AdaptiveDpr } from '@react-three/drei';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { useGSAP, refreshStory, reduceQuery } from '../lib/gsap';
import type { SceneProps } from '../components/SceneViewport';
import { OceanScene } from './OceanScene';
import { SonarScene } from './SonarScene';
import { PipelineScene } from './PipelineScene';
import { ComparisonScene } from './ComparisonScene';
import { BeaconScene } from './BeaconScene';

export default function SceneRoot({ kind, progress, active }: SceneProps) {
  const scope = useRef<HTMLDivElement>(null);
  const [reduced, setReduced] = useState(() => window.matchMedia(reduceQuery).matches);
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 767px)').matches);
  useGSAP(() => {
    const reduce = window.matchMedia(reduceQuery);
    const small = window.matchMedia('(max-width: 767px)');
    const update = () => { setReduced(reduce.matches); setMobile(small.matches); };
    reduce.addEventListener('change', update);
    small.addEventListener('change', update);
    return () => {
      reduce.removeEventListener('change', update);
      small.removeEventListener('change', update);
    };
  }, { scope });
  return (
    <div ref={scope} className="canvas-host" aria-hidden="true">
      <Canvas
        orthographic={kind === 'comparison'}
        camera={{ position: [0, 0, 12], fov: 38, near: .1, far: 150, zoom: kind === 'comparison' ? 60 : 1 }}
        dpr={[1, mobile ? 1.5 : 1.75]}
        frameloop={active && !reduced ? 'always' : 'demand'}
        gl={{ alpha: true, antialias: !mobile, powerPreference: 'high-performance' }}
        onCreated={() => { requestAnimationFrame(refreshStory); }}
      >
        <Suspense fallback={null}>
          <ambientLight intensity={0.6} color="#8cc9c8" />
          <directionalLight position={[4, 12, 7]} intensity={2.1} color="#b6d5d0" />
          <pointLight position={[-6, 3, 5]} intensity={18} color="#3b9a93" />
          {kind === 'hero' && <OceanScene progress={progress} reduced={reduced} mobile={mobile} />}
          {kind === 'sonar' && <SonarScene progress={progress} reduced={reduced} />}
          {kind === 'pipeline' && <PipelineScene progress={progress} reduced={reduced} />}
          {kind === 'comparison' && <ComparisonScene progress={progress} reduced={reduced} />}
          {kind === 'beacon' && <BeaconScene progress={progress} reduced={reduced} />}
          {!mobile && !reduced && (kind === 'hero' || kind === 'beacon' || kind === 'pipeline') && (
            <EffectComposer multisampling={0}>
              <Bloom intensity={0.22} luminanceThreshold={0.85} mipmapBlur />
            </EffectComposer>
          )}
          <AdaptiveDpr pixelated />
        </Suspense>
      </Canvas>
    </div>
  );
}
