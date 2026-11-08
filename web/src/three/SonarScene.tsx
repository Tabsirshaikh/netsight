import { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGSAP, type Progress } from '../lib/gsap';
import { makeTowfish, disposeObject } from './models';
import { waterfallVertex, waterfallFragment } from './shaders/waterfall.glsl';
import { pingVertex, pingFragment } from './shaders/ocean.glsl';

export function SonarScene({ progress, reduced }: { progress: Progress; reduced: boolean }) {
  const { camera, gl, size } = useThree();
  const scope = useRef(gl.domElement);
  const fish = useMemo(makeTowfish, []);
  const image = useMemo(() => ({
    uProgress: { value: 0 }, uTime: { value: 0 }, uStretch: { value: 1 }
  }), []);
  const ping = useMemo(() => ({ uTime: { value: 0 }, uReveal: { value: 0.7 } }), []);
  useGSAP(() => {
    fish.position.set(0, 3.05, .35);
    fish.scale.setScalar(.48);
    return () => disposeObject(fish);
  }, { scope, dependencies: [fish] });

  useFrame(() => {
    const aspect = size.width / size.height;
    const distance = Math.max(11.5, 12 / (2 * Math.tan(THREE.MathUtils.degToRad(19)) * aspect));
    camera.position.set(0, 0, distance);
    camera.lookAt(0, 0, 0);
    image.uProgress.value = reduced ? 1 : progress.current;
    image.uTime.value = progress.current * 20;
    ping.uTime.value = reduced ? 2.8 : progress.current * 27;
    ping.uReveal.value = reduced ? .25 : .5;
  });

  return (
    <>
      <mesh position={[0, -.25, 0]}>
        <planeGeometry args={[11, 5.5]} />
        <shaderMaterial uniforms={image} vertexShader={waterfallVertex} fragmentShader={waterfallFragment} />
      </mesh>
      <mesh position={[0, -.1, .05]}>
        <planeGeometry args={[11, 5.5]} />
        <shaderMaterial uniforms={ping} vertexShader={pingVertex} fragmentShader={pingFragment}
          transparent depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <primitive object={fish} />
      <mesh position={[0, -.25, -.05]}>
        <boxGeometry args={[11.1, 5.6, .06]} /><meshStandardMaterial color="#17383c" />
      </mesh>
    </>
  );
}
