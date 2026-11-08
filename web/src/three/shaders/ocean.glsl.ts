export const waterVertex = /* glsl */ `
  uniform float uTime;
  varying vec2 vUv;
  varying float vWave;
  void main() {
    vUv = uv;
    vec3 p = position;
    float a = sin(p.x * .32 + uTime * .3);
    float b = sin(p.y * .41 - uTime * .22);
    p.z += a * b * .24;
    vWave = a * b;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
  }
`;

export const waterFragment = /* glsl */ `
  uniform float uTime;
  varying vec2 vUv;
  varying float vWave;
  void main() {
    float threads = pow(max(0., sin(vUv.x * 180. + sin(vUv.y * 85. + uTime * .2) * 3.)), 16.);
    vec3 deep = vec3(.012, .067, .095);
    vec3 glint = vec3(.09, .24, .26);
    vec3 color = mix(deep, glint, vWave * .32 + .35);
    color += threads * .035;
    gl_FragColor = vec4(color, .78);
  }
`;

export const seabedVertex = /* glsl */ `
  varying vec2 vUv;
  varying float vHeight;
  void main() {
    vUv = uv;
    vec3 p = position;
    p.z += sin(p.x * .4) * cos(p.y * .32) * .4;
    p.z += sin(p.x * 1.3 + p.y * .4) * .06;
    vHeight = p.z;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(p, 1.);
  }
`;

export const seabedFragment = /* glsl */ `
  uniform float uTime;
  varying vec2 vUv;
  varying float vHeight;
  float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
  void main() {
    vec2 uv = vUv * 25.;
    float ripples = .5 + .5 * sin(uv.y * 13. + sin(uv.x * 1.4) * 2.);
    float noise = hash(floor(vUv * 1100.));
    // Moving caustic intersections indicate light arriving from the surface.
    float a = abs(sin(uv.x * 1.8 + sin(uv.y * 1.5 + uTime * .15)));
    float b = abs(cos(uv.y * 1.7 + sin(uv.x * 1.4 - uTime * .12)));
    float caustic = pow(max(0., 1. - a * b), 24.);
    vec3 color = vec3(.018, .075, .079);
    color += ripples * vec3(.012, .021, .018);
    color += caustic * vec3(.014, .04, .032);
    color += noise * .012 + vHeight * .015;
    gl_FragColor = vec4(color, 1.);
  }
`;

export const pingVertex = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
  }
`;

export const pingFragment = /* glsl */ `
  uniform float uTime;
  uniform float uReveal;
  varying vec2 vUv;
  void main() {
    vec2 p = (vUv - .5) * vec2(1.3, 1.);
    float radius = length(p);
    float travel = fract(uTime * .18);
    float ring = exp(-pow((radius - travel * .85) * 100., 2.));
    float previous = exp(-pow((radius - (travel * .85 - .24)) * 130., 2.)) * .22;
    // Two lateral fans: the center is deliberately not illuminated.
    float fan = smoothstep(.1, .3, abs(p.x) - abs(p.y) * .35);
    float falloff = 1. - smoothstep(.45, .85, radius);
    float alpha = (ring + previous) * fan * falloff * uReveal * .7;
    gl_FragColor = vec4(.32, .91, .75, alpha);
  }
`;
