export const waterfallVertex = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.);
  }
`;

export const waterfallFragment = /* glsl */ `
  uniform float uProgress;
  uniform float uTime;
  uniform float uStretch;
  varying vec2 vUv;

  float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
  }
  float box(vec2 p, vec2 b) {
    vec2 d = abs(p) - b;
    return 1. - smoothstep(-.008, .008, max(d.x, d.y));
  }
  void main() {
    vec2 p = (vUv - .5) * 2.;
    p.y *= uStretch;
    float noise = hash(floor(vUv * vec2(1150., 740.)));
    float sand = .24 + .065 * sin(p.y * 130. + sin(p.x * 9.) * 2.);
    sand += (noise - .5) * .24;
    float attenuation = 1. - abs(p.x) * .3;

    vec2 net = p - vec2(-.48, -.05);
    net = mat2(.94, -.34, .34, .94) * net;
    float netShape = box(net, vec2(.19, .15));
    float mesh = max(
      pow(.5 + .5 * cos(net.x * 175.), 12.),
      pow(.5 + .5 * cos(net.y * 175.), 12.)
    );
    float netShadow = box(net - vec2(-.18, -.015), vec2(.20, .14)) * (1. - netShape);
    sand *= 1. - netShadow * .85;
    sand += netShape * (.10 + mesh * .55);

    vec2 trap = p - vec2(.46, .32);
    trap = mat2(.98, .18, -.18, .98) * trap;
    float trapShape = box(trap, vec2(.075, .10));
    float trapInner = box(trap, vec2(.052, .074));
    float trapShadow = box(trap - vec2(.18, -.025), vec2(.15, .095)) * (1. - trapShape);
    sand *= 1. - trapShadow * .9;
    sand += trapShape * .60 - trapInner * .28;

    float nadir = smoothstep(.055, .085, abs(p.x));
    sand = mix(.008 + noise * .015, sand * attenuation, nadir);
    float row = 1. - vUv.y;
    float reveal = 1. - smoothstep(uProgress, uProgress + .008, row);
    float scanning = exp(-pow((row - uProgress) * 220., 2.));
    float scanNoise = sin(vUv.y * 1400. + uTime) * .006;
    vec3 color = sand * vec3(.55, .86, .76);
    color += scanNoise;
    color = mix(vec3(.009, .025, .030), color, reveal);
    color += scanning * vec3(.20, .60, .46) * step(.01, uProgress) * step(uProgress, .995);
    gl_FragColor = vec4(color, 1.);
  }
`;
