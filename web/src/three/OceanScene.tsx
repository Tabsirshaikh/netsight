import { useMemo, useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';
import { useGSAP, type Progress } from '../lib/gsap';
import { makeVessel, makeTowfish, makeDebris, disposeObject } from './models';
import {
  waterVertex, waterFragment, seabedVertex, seabedFragment, pingVertex, pingFragment
} from './shaders/ocean.glsl';

export function OceanScene({ progress, reduced, mobile }: {
  progress: Progress; reduced: boolean; mobile: boolean;
}) {
  const { camera, gl, clock } = useThree();
  const scope = useRef(gl.domElement);
  const vessel = useMemo(makeVessel, []);
  const fish = useMemo(makeTowfish, []);
  const debris = useMemo(makeDebris, []);
  const water = useMemo(() => ({ uTime: { value: 0 } }), []);
  const bed = useMemo(() => ({ uTime: { value: 0 } }), []);
  const ping = useMemo(() => ({ uTime: { value: 0 }, uReveal: { value: 0 } }), []);
  const cable = useMemo(() => {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-2.5, .3, 0),
      new THREE.Vector3(-4, -1, 0),
      new THREE.Vector3(-5, -3, .4),
      new THREE.Vector3(-5.2, -4.5, 1)
    ]);
    return new THREE.TubeGeometry(curve, 36, .025, 4, false);
  }, []);
  const particles = useMemo(() => {
    const count = mobile ? 75 : 220;
    const vertices = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      vertices[i * 3] = Math.sin(i * 93.3) * 19;
      vertices[i * 3 + 1] = -1 - (i % 37) * .2;
      vertices[i * 3 + 2] = Math.cos(i * 47.1) * 15;
    }
    return vertices;
  }, [mobile]);

  useGSAP(() => {
    fish.position.set(-5.2, -4.5, 1);
    debris.position.y = -8.7;
    return () => {
      disposeObject(vessel);
      disposeObject(fish);
      disposeObject(debris);
      cable.dispose();
    };
  }, { scope, dependencies: [vessel, fish, debris, cable] });

  useFrame(() => {
    const p = progress.current;
    const dive = THREE.MathUtils.smoothstep(p, .23, .91);
    const time = reduced ? 0 : clock.elapsedTime;
    camera.position.set(13 - dive * 4, 5.5 - dive * 11, 19 - dive * 3);
    camera.lookAt(-1.2, -1 - dive * 5.4, 0);
    vessel.position.y = Math.sin(time * .6) * .07;
    vessel.rotation.z = Math.sin(time * .45) * .015;
    water.uTime.value = time;
    bed.uTime.value = time;
    ping.uTime.value = reduced ? 2.8 : time;
    ping.uReveal.value = THREE.MathUtils.smoothstep(p, .3, .6);
  });

  return (
    <>
      <fogExp2 attach="fog" args={['#04131c', .026]} />
      <primitive object={vessel} />
      <primitive object={fish} />
      <mesh geometry={cable}><meshStandardMaterial color="#7c9290" roughness={0.7} /></mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={2}>
        <planeGeometry args={[110, 110, mobile ? 30 : 65, mobile ? 30 : 65]} />
        <shaderMaterial uniforms={water} vertexShader={waterVertex} fragmentShader={waterFragment}
          transparent side={THREE.DoubleSide} depthWrite={false} />
      </mesh>
      <mesh position={[0, -9, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[75, 75, 90, 90]} />
        <shaderMaterial uniforms={bed} vertexShader={seabedVertex} fragmentShader={seabedFragment} />
      </mesh>
      <primitive object={debris} />
      <mesh position={[-5, -8.65, 1]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[40, 32]} />
        <shaderMaterial uniforms={ping} vertexShader={pingVertex} fragmentShader={pingFragment}
          transparent depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      <points>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[particles, 3]} /></bufferGeometry>
        <pointsMaterial color="#a5d9ca" size={0.022} transparent opacity={0.3} depthWrite={false} />
      </points>
    </>
  );
}
