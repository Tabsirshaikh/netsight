import * as THREE from 'three';

const ink = 0x102932;
const mint = 0x6de2c3;
const warm = 0xf4ab71;

function standard(color: number, metalness = 0.35) {
  return new THREE.MeshStandardMaterial({ color, metalness, roughness: 0.55 });
}

function box(group: THREE.Group, dimensions: [number, number, number], position: [number, number, number], material: THREE.Material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...dimensions), material);
  mesh.position.set(...position);
  group.add(mesh);
  return mesh;
}

export function makeVessel() {
  const group = new THREE.Group();
  const hullMaterial = standard(0x25434a);
  const deckMaterial = standard(0xa0aca4);
  const dark = standard(ink);
  const shape = new THREE.Shape();
  shape.moveTo(-2.8, 0);
  shape.lineTo(-1.9, -.72);
  shape.lineTo(1.75, -.72);
  shape.quadraticCurveTo(2.8, -.55, 3.2, 0);
  shape.quadraticCurveTo(2.8, .55, 1.75, .72);
  shape.lineTo(-1.9, .72);
  shape.closePath();
  const hull = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, {
    depth: .7, bevelEnabled: true, bevelSize: .12, bevelThickness: .15, bevelSegments: 2, steps: 1
  }), hullMaterial);
  hull.rotation.x = -Math.PI / 2;
  hull.position.y = -.4;
  group.add(hull);
  box(group, [3.8, .12, 1.15], [-.1, .36, 0], deckMaterial);
  box(group, [1.45, .85, 1.03], [.6, .82, 0], deckMaterial);
  box(group, [1.52, .22, 1.10], [.6, 1.39, 0], dark);
  box(group, [.12, 1.2, .12], [.5, 1.9, 0], dark);
  box(group, [1.8, .12, .1], [.5, 2.35, 0], deckMaterial);
  box(group, [.8, .20, 1.05], [.65, 1.02, 0], standard(0x173a45, .7));
  const rail = standard(0x688c8d);
  for (const z of [-.63, .63]) {
    box(group, [2.6, .04, .04], [-.7, .72, z], rail);
    for (let i = 0; i < 5; i++) box(group, [.035, .35, .035], [-1.9 + i * .6, .55, z], rail);
  }
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(.07, 8, 8),
    new THREE.MeshBasicMaterial({ color: warm }));
  lamp.position.set(.5, 2.52, 0);
  group.add(lamp);
  return group;
}

export function makeTowfish() {
  const group = new THREE.Group();
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(.20, 1.7, 5, 12), standard(warm, .55));
  body.rotation.z = Math.PI / 2;
  group.add(body);
  const tail = box(group, [.65, .045, .85], [-.9, 0, 0], standard(ink));
  tail.rotation.y = .08;
  box(group, [.5, .5, .035], [-.9, .1, 0], standard(ink));
  for (const z of [-.19, .19]) {
    box(group, [1.15, .06, .055], [0, -.05, z], new THREE.MeshStandardMaterial({
      color: mint, emissive: mint, emissiveIntensity: .25, roughness: .4
    }));
  }
  return group;
}

export function makeDebris() {
  const group = new THREE.Group();
  const netMaterial = new THREE.LineBasicMaterial({ color: 0x4d8277 });
  const points: number[] = [];
  for (let i = 0; i < 12; i++) {
    const n = -1.6 + i * .29;
    for (let j = 0; j < 15; j++) {
      const a = -2 + j * .28;
      const b = a + .28;
      points.push(n, Math.sin(a * 2) * .08, a, n, Math.sin(b * 2) * .08, b);
      points.push(a * .8, Math.cos(a) * .07, n, b * .8, Math.cos(b) * .07, n);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  const net = new THREE.LineSegments(geometry, netMaterial);
  net.position.set(-3, 0, 1);
  net.rotation.y = .4;
  group.add(net);
  const trap = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(1.1, .7, .9)),
    new THREE.LineBasicMaterial({ color: 0x75958b })
  );
  trap.position.set(3, .35, -1.5);
  group.add(trap);
  return group;
}

function segment(group: THREE.Group, points: THREE.Vector3[], color = mint) {
  const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),
    new THREE.LineBasicMaterial({ color, transparent: true, opacity: .7 }));
  group.add(line);
}

export function makePipelineBlock(index: number) {
  const group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({
    color: 0x14323b, metalness: .6, roughness: .38,
    emissive: mint, emissiveIntensity: .035
  });
  box(group, [2.65, .22, 1.85], [0, 0, 0], material);
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(2.66, .23, 1.86)),
    new THREE.LineBasicMaterial({ color: mint, transparent: true, opacity: .5 })
  );
  group.add(edges);
  const v = (x: number, z: number) => new THREE.Vector3(x, .14, z);

  if (index === 0) {
    for (let i = -4; i <= 4; i++) {
      segment(group, [v(i * .25, -.7), v(i * .25, .7)]);
      segment(group, [v(-1, i * .16), v(1, i * .16)]);
    }
  } else if (index === 1) {
    for (let i = 0; i < 3; i++) {
      const x = -.8 + i * .75;
      segment(group, [v(x, -.4), v(x + .45, -.4), v(x + .45, .35), v(x, .35), v(x, -.4)], warm);
    }
  } else if (index === 2) {
    for (let i = 0; i < 9; i++) {
      segment(group, [v(-1, -.65 + i * .15), v(.75, -.45 + i * .15)]);
      segment(group, [v(-1 + i * .22, -.65), v(-.8 + i * .22, .65)]);
    }
  } else if (index === 3) {
    for (let i = 0; i < 7; i++) {
      box(group, [.15, .06 + i * .055, .5], [-.9 + i * .3, .19 + i * .0275, 0], standard(mint));
    }
    segment(group, [v(-1, .55), v(1, -.55)], warm);
  } else if (index === 4) {
    [mint, warm, 0xd97c7c].forEach((color, i) => {
      box(group, [.48, .06, .9], [-.75 + i * .75, .18, 0], new THREE.MeshStandardMaterial({
        color, emissive: color, emissiveIntensity: .2
      }));
    });
  } else {
    for (let i = 0; i < 4; i++) {
      const x = -.95 + i * .5;
      segment(group, [v(x, -.3), v(x + .32, -.3), v(x + .32, .3), v(x, .3), v(x, -.3)]);
      if (i < 3) segment(group, [v(x + .32, 0), v(x + .5, 0)], warm);
    }
  }
  group.userData.bodyMaterial = material;
  return group;
}

/** Primitives are owned here, not auto-disposed by R3F. */
export function disposeObject(object: THREE.Object3D) {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  object.traverse(child => {
    const renderable = child as THREE.Mesh;
    if (renderable.geometry) geometries.add(renderable.geometry);
    if (renderable.material) {
      const list = Array.isArray(renderable.material) ? renderable.material : [renderable.material];
      list.forEach(material => materials.add(material));
    }
  });
  geometries.forEach(geometry => geometry.dispose());
  materials.forEach(material => material.dispose());
}
