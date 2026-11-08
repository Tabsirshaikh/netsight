import { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGSAP, type Progress } from '../lib/gsap';
import { makePipelineBlock, disposeObject } from './models';
import { pingVertex, pingFragment } from './shaders/ocean.glsl';

export function BeaconScene({ progress, reduced }: { progress: Progress; reduced: boolean }) {
  const { gl, camera, size } = useThree();
  const scope = useRef(gl.domElement);
  const blocks = useMemo(() => Array.from({ length: 6 }, (_, i) => makePipelineBlock(i)), []);
  const group = useRef<THREE.Group>(null);
  const ping = useMemo(() => ({ uTime: { value: 0 }, uReveal: { value: .6 } }), []);
  const lines = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(36), 3));
    return geometry;
  }, []);
  useGSAP(() => () => { blocks.forEach(disposeObject); lines.dispose(); }, { scope, dependencies: [blocks, lines] });
  useFrame(({ clock }) => {
    const p = reduced ? 1 : progress.current;
    const time = reduced ? 0 : clock.elapsedTime;
    camera.position.set(0, 7, size.width / size.height < 1 ? 21 : 15);
    camera.lookAt(0, 0, 0);
    blocks.forEach((block, i) => {
      const angle = i * Math.PI / 3;
      const radius = THREE.MathUtils.lerp(6, 3.7, p);
      block.position.set(Math.cos(angle) * radius, Math.sin(time * .3 + i) * .05, Math.sin(angle) * radius);
      block.rotation.y = -angle;
      block.scale.setScalar(.55);
      const positions = lines.attributes.position as THREE.BufferAttribute;
      positions.setXYZ(i * 2, 0, 0, 0);
      positions.setXYZ(i * 2 + 1, block.position.x, block.position.y, block.position.z);
    });
    lines.attributes.position.needsUpdate = true;
    if (group.current) group.current.rotation.y = -.4 + p * .4;
    ping.uTime.value = reduced ? 2.8 : time;
  });
  return (
    <group ref={group}>
      {blocks.map((block, i) => <primitive object={block} key={i} />)}
      <lineSegments geometry={lines}><lineBasicMaterial color="#6de2c3" transparent opacity={0.17} /></lineSegments>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -.2, 0]}>
        <planeGeometry args={[24, 24]} />
        <shaderMaterial vertexShader={pingVertex} fragmentShader={pingFragment} uniforms={ping}
          transparent depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.0, .018, 8, 90]} /><meshBasicMaterial color="#6de2c3" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[.08, .15, 24]} /><meshBasicMaterial color="#f4ab71" side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}
