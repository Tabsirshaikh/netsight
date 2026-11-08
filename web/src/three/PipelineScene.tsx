import { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGSAP, type Progress } from '../lib/gsap';
import { makePipelineBlock, disposeObject } from './models';

export function PipelineScene({ progress, reduced }: { progress: Progress; reduced: boolean }) {
  const { camera, gl, size } = useThree();
  const scope = useRef(gl.domElement);
  const group = useRef<THREE.Group>(null);
  const blocks = useMemo(() => Array.from({ length: 6 }, (_, i) => makePipelineBlock(i)), []);
  const wire = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(5 * 6), 3));
    return geometry;
  }, []);
  useGSAP(() => () => {
    blocks.forEach(disposeObject);
    wire.dispose();
  }, { scope, dependencies: [blocks, wire] });

  useFrame(() => {
    const p = progress.current;
    const expand = reduced ? 1 : Math.min(
      THREE.MathUtils.smoothstep(p, .06, .25),
      1 - THREE.MathUtils.smoothstep(p, .84, .97)
    );
    const active = Math.min(5, Math.max(0, Math.floor((p - .22) / .095)));
    const aspect = size.width / size.height;
    camera.position.set(7.8, 7.3, Math.max(12.5, 12 / Math.max(.7, aspect)));
    camera.lookAt(0, .1, 0);
    blocks.forEach((block, i) => {
      const x = ((i % 3) - 1) * 3.35;
      const z = i < 3 ? -1.5 : 1.8;
      const y = i < 3 ? .9 : -.55;
      block.position.set(x * expand, THREE.MathUtils.lerp((i - 2.5) * .29, y, expand), z * expand);
      block.rotation.y = (i % 2 ? -.07 : .07) * expand;
      const material = block.userData.bodyMaterial as THREE.MeshStandardMaterial;
      material.emissiveIntensity = reduced ? .12 : i === active && expand > .8 ? .35 : .035;
      block.scale.setScalar(!reduced && i === active && expand > .8 ? 1.045 : 1);
    });
    const positions = wire.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < 5; i++) {
      positions.setXYZ(i * 2, blocks[i].position.x, blocks[i].position.y, blocks[i].position.z);
      positions.setXYZ(i * 2 + 1, blocks[i + 1].position.x, blocks[i + 1].position.y, blocks[i + 1].position.z);
    }
    positions.needsUpdate = true;
    if (group.current) group.current.rotation.y = THREE.MathUtils.lerp(-.22, .12, p);
  });

  return (
    <group ref={group}>
      {blocks.map((block, i) => <primitive key={i} object={block} />)}
      <lineSegments geometry={wire}>
        <lineBasicMaterial color="#6de2c3" transparent opacity={0.23} />
      </lineSegments>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2.3, 0]}>
        <planeGeometry args={[26, 26]} />
        <meshStandardMaterial color="#04141c" roughness={0.9} transparent opacity={0.35} />
      </mesh>
      <gridHelper args={[22, 24, '#153a40', '#0c242d']} position={[0, -2.29, 0]} />
    </group>
  );
}
