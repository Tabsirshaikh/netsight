import { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGSAP, type Progress } from '../lib/gsap';
import { content } from '../content';
import { disposeObject } from './models';

export function ComparisonScene({ progress, reduced }: { progress: Progress; reduced: boolean }) {
  const { camera, gl, size } = useThree();
  const scope = useRef(gl.domElement);
  const bars = useMemo(() => content.s04.columns.map((column, i) => {
    const group = new THREE.Group();
    const geometry = new THREE.BoxGeometry(1, 1, .55);
    const material = new THREE.MeshStandardMaterial({
      color: i === 2 ? '#f4ab71' : '#265c60',
      emissive: i === 2 ? '#774424' : '#102f32',
      emissiveIntensity: .18, metalness: .4, roughness: .5
    });
    group.add(new THREE.Mesh(geometry, material));
    group.add(new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: i === 2 ? '#ffd3ad' : '#6d9b98', transparent: true, opacity: .6 })
    ));
    group.userData.value = column.value;
    return group;
  }), []);
  useGSAP(() => () => bars.forEach(disposeObject), { scope, dependencies: [bars] });
  useFrame(() => {
    const orthographic = camera as THREE.OrthographicCamera;
    const zoom = size.height / 3.65;
    if (orthographic.zoom !== zoom) {
      orthographic.zoom = zoom;
      orthographic.updateProjectionMatrix();
    }
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    const worldWidth = size.width / zoom;
    bars.forEach((bar, i) => {
      const p = reduced ? 1 : THREE.MathUtils.clamp((progress.current - i * .12) / .4, 0, 1);
      const height = 2.85 * bar.userData.value / content.s04.columns[0].value * p;
      bar.scale.set(Math.min(1.8, worldWidth * .14), Math.max(.006, height), 1);
      bar.position.set((i - 1) * worldWidth / 3, -1.45 + height / 2, 0);
      bar.rotation.y = -.24;
    });
  });
  return (
    <>
      {bars.map((bar, i) => <primitive key={i} object={bar} />)}
      <gridHelper args={[70, 70, '#254148', '#0d262e']} rotation={[Math.PI / 2, 0, 0]} position={[0, 0, -1]} />
    </>
  );
}
