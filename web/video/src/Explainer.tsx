import type { CSSProperties } from 'react';
import {
  AbsoluteFill,
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig
} from 'remotion';
import { content } from '../../src/content';
import { partB } from '../../src/content.partB';

const colors = {
  ocean: '#030d14',
  panel: '#071820',
  ink: '#e4eeec',
  muted: '#a7bdb5',
  mint: '#6de2c3',
  warm: '#f4ab71',
  line: '#35534d'
};

const clamp = {
  extrapolateLeft: 'clamp' as const,
  extrapolateRight: 'clamp' as const
};

const mono: CSSProperties = {
  fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
  letterSpacing: 2
};

function ramp(frame: number, start: number, end: number): number {
  return interpolate(frame, [start, end], [0, 1], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic)
  });
}

/**
 * Frame-pure procedural composition.
 * No network assets, audio, random values or wall-clock animation.
 * The entire film is rendered with vector geometry and DOM typography.
 */
export function Explainer() {
  const frame = useCurrentFrame();
  const { width, height, fps } = useVideoConfig();
  const stageLength = fps * 4;
  const chapter = Math.min(4, Math.floor(frame / stageLength));
  const local = frame - chapter * stageLength;
  const chapterText = partB.video.stages[chapter]!;
  const enter = ramp(local, 0, 17);
  const exit = chapter === 4 ? 1 : 1 - ramp(local, 105, 120);
  const opacity = enter * exit;
  const waterfall = ramp(frame, 125, 226);
  const boxes = ramp(frame, 248, 286);
  const calibration = ramp(frame, 365, 422);
  const report = ramp(frame, 485, 530);

  return (
    <AbsoluteFill style={{ background: colors.ocean, color: colors.ink, fontFamily: '"Space Grotesk", Arial, sans-serif' }}>
      <AbsoluteFill style={{
        background: 'radial-gradient(ellipse at 75% 45%, #123e36 0%, #071c23 35%, #030d14 75%)'
      }} />
      <svg width={width} height={height} viewBox="0 0 1920 1080" style={{ position: 'absolute' }}>
        <defs>
          <pattern id="film-grid" width="70" height="70" patternUnits="userSpaceOnUse">
            <path d="M70 0H0V70" fill="none" stroke="#6de2c3" strokeOpacity=".05" />
          </pattern>
          <pattern id="waterfall-noise" width="18" height="9" patternUnits="userSpaceOnUse">
            <path d="M0 1H18M3 5H13" stroke="#b9c7a5" strokeOpacity=".25" />
            <path d="M0 8H18" stroke="#021018" strokeOpacity=".6" />
          </pattern>
          <pattern id="pot-mesh" width="13" height="13" patternUnits="userSpaceOnUse">
            <path d="M0 0H13V13" fill="none" stroke="#ced5b3" strokeWidth="1.2" />
          </pattern>
          <linearGradient id="sonar-bed" x1="0" y1="0" x2="1" y2=".2">
            <stop stopColor="#10262b" />
            <stop offset=".6" stopColor="#3a5b48" />
            <stop offset="1" stopColor="#102b2b" />
          </linearGradient>
          <clipPath id="waterfall-clip">
            <rect x="890" y="260" width="850" height={510 * waterfall} />
          </clipPath>
        </defs>

        <rect width="1920" height="1080" fill="url(#film-grid)" />

        {chapter === 0 && (
          <g opacity={opacity}>
            <path d="M770 300Q1200 260 1790 300" fill="none" stroke="#789b9a" strokeOpacity=".5" />
            <path d="M1110 280L1230 280 1210 309H1130Z" fill="#879f9a" />
            <path d="M1145 280V248H1185V280M1167 248V226" fill="none" stroke="#c2d6cb" strokeWidth="4" />
            <path d="M1220 304Q1360 390 1350 492" fill="none" stroke="#9cbbb0" strokeWidth="2" />
            <g transform="translate(1350 500) rotate(-12)">
              <path d="M-70 0Q-45-28 52-14L79 0 50 14Q-45 28-70 0" fill="#9eb5a5" stroke="#d5e4cd" />
              <path d="M-35 5L-68 30-40-7M10 5L34 30 25-7" fill="#3c7268" />
            </g>
            <path d="M800 830Q1030 770 1260 814T1810 825" fill="none" stroke="#7b9d7e" strokeWidth="3" />
            {Array.from({ length: 5 }, (_, i) => {
              const p = ((local + i * 22) % 110) / 110;
              return (
                <g key={i} opacity={(1 - p) * .7}>
                  <path
                    d={`M1350 510L${1350 - p * 510} ${510 + p * 310}Q1350 ${540 + p * 420} ${1350 + p * 410} ${510 + p * 310}Z`}
                    fill="#6de2c3"
                    fillOpacity=".035"
                    stroke="#6de2c3"
                    strokeWidth="2"
                  />
                </g>
              );
            })}
            <text x="1320" y="575" fill={colors.muted} fontSize="18" style={mono}>{content.s01.towfish}</text>
          </g>
        )}

        {(chapter === 1 || chapter === 2) && (
          <g opacity={opacity}>
            <rect x="878" y="248" width="874" height="534" fill="#071820" stroke={colors.line} />
            <g clipPath="url(#waterfall-clip)">
              <rect x="890" y="260" width="850" height="510" fill="url(#sonar-bed)" />
              {Array.from({ length: 32 }, (_, i) => (
                <path key={i} d={`M890 ${270 + i * 17}Q1190 ${230 + i * 17} 1740 ${300 + i * 17}`} fill="none" stroke="#9cb792" strokeOpacity=".19" />
              ))}
              <rect x="1285" y="260" width="42" height="510" fill="#020c13" />
              <g transform="translate(1100 480) rotate(-17)">
                <path d="M-55-50H44L130-10 112 95 20 57Z" fill="#020c13" />
                <path d="M-55-50H44V58H-55Z" fill="url(#pot-mesh)" stroke="#d7deb7" strokeWidth="3" />
                <ellipse cy="5" rx="16" ry="24" fill="#172c24" stroke="#cbd7b0" />
              </g>
              <g transform="translate(1530 610) rotate(18)">
                <path d="M-30-24Q68-39 116-4L106 45-5 29Z" fill="#020c13" />
                <ellipse rx="32" ry="25" fill="#b1c2a0" />
              </g>
              <rect x="890" y="260" width="850" height="510" fill="url(#waterfall-noise)" />
            </g>
            {chapter === 1 && (
              <>
                <path d={`M890 ${260 + 510 * waterfall}H1740`} stroke={colors.mint} strokeWidth="2" />
                <text x="1306" y="823" fill={colors.muted} fontSize="19" textAnchor="middle" style={mono}>{content.s02.nadir}</text>
              </>
            )}
            {chapter === 2 && (
              <g fill="none" stroke={colors.mint} strokeWidth="3">
                <rect x="1005" y="388" width="181" height="185" strokeDasharray="732" strokeDashoffset={732 * (1 - boxes)} />
                <rect x="1471" y="558" width="123" height="110" strokeDasharray="466" strokeDashoffset={466 * (1 - boxes)} />
                <g opacity={boxes}>
                  <path d="M1186 388L1260 352H1420" strokeWidth="1" />
                  <text x="1270" y="340" fill={colors.ink} stroke="none" fontSize="18" style={mono}>{content.s02.trap}</text>
                </g>
              </g>
            )}
          </g>
        )}

        {chapter === 3 && (
          <g opacity={opacity}>
            <rect x="890" y="265" width="850" height="510" fill="#071820" stroke={colors.line} />
            <path d="M975 670H1630M975 670V335" fill="none" stroke="#91b49b77" />
            <path d="M975 670L1625 335" fill="none" stroke="#cfe4d1" strokeDasharray="8 10" opacity=".6" />
            {[.2, .4, .6, .8, 1].map((p, i) => {
              const finalHeight = p * 310;
              const rawHeight = finalHeight * ([.36, .48, .6, .7, .76][i] ?? .5);
              const h = rawHeight + (finalHeight - rawHeight) * calibration;
              return (
                <rect key={p} x={1000 + i * 135} y={670 - h} width="40" height={h} fill={colors.mint} opacity=".85" />
              );
            })}
            <text x="1310" y="718" fill={colors.muted} fontSize="17" textAnchor="middle" style={mono}>{partB.trust.diagramNote}</text>
            <g transform={`translate(1110 ${245 - calibration * 25})`}>
              <rect width="410" height="56" rx="3" fill="#112d27" stroke={colors.mint} />
              <text x="205" y="36" textAnchor="middle" fill={colors.mint} fontSize="20" style={mono}>{content.s06.levels[0].name}</text>
            </g>
            <text x="1310" y="834" fill={colors.muted} fontSize="20" textAnchor="middle" style={mono}>{content.s06.calibration}</text>
          </g>
        )}

        {chapter === 4 && (
          <g opacity={opacity}>
            <g transform={`translate(${900 + (1 - report) * 65} 260)`} opacity={report}>
              <rect width="460" height="500" fill="#092128" stroke={colors.line} />
              <text x="35" y="58" fill={colors.ink} fontSize="30">{content.s09.title}</text>
              <text x="35" y="93" fill={colors.mint} fontSize="15" style={mono}>JSON + REPORT</text>
              {content.s09.fields.map((field, i) => {
                const p = ramp(local, 8 + i * 5, 23 + i * 5);
                return (
                  <g key={field} opacity={p} transform={`translate(${(1 - p) * 20} 0)`}>
                    <path d={`M35 ${145 + i * 52}H425`} stroke={colors.line} />
                    <text x="35" y={177 + i * 52} fill="#bfd6c8" fontSize="19">{field}</text>
                  </g>
                );
              })}
            </g>
            {Array.from({ length: 4 }, (_, i) => {
              const p = ramp(local, 25 + i * 11, 43 + i * 11);
              return (
                <g key={i} opacity={p}>
                  {i > 0 && <path d={`M1575 ${295 + (i - 1) * 122 + 75}V${295 + i * 122}`} stroke={colors.mint} />}
                  <rect x="1440" y={295 + i * 122} width="270" height="75" fill="#0b2929" stroke="#6de2c377" />
                  <text x="1460" y={340 + i * 122} fill={colors.mint} fontSize="17" style={mono}>{partB.ledger.payloadNames[i]}</text>
                </g>
              );
            })}
            <text x="1320" y="845" fill={colors.warm} fontSize="20" textAnchor="middle">{content.s09.disclaimer}</text>
          </g>
        )}
      </svg>

      <div style={{
        position: 'absolute', top: 65, left: 105, right: 105,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
      }}>
        <div style={{ fontSize: 34, letterSpacing: -2 }}>{content.brand}<span style={{ color: colors.mint }}>.</span></div>
        <div style={{ ...mono, fontSize: 17, color: colors.muted }}>{content.ui.research} / {content.team}</div>
      </div>

      <div style={{
        position: 'absolute', top: 300, left: 105, width: 690,
        opacity, transform: `translateY(${(1 - enter) * 18}px)`
      }}>
        <div style={{ ...mono, fontSize: 18, color: colors.mint, marginBottom: 33 }}>
          0{chapter + 1} / {partB.video.title}
        </div>
        <h1 style={{
          fontSize: 78, lineHeight: 1.06, fontWeight: 500,
          letterSpacing: -4.5, margin: '0 0 35px', maxWidth: 650
        }}>{chapterText.title}</h1>
        <p style={{ fontSize: 26, lineHeight: 1.65, color: colors.muted, maxWidth: 615 }}>{chapterText.body}</p>
        {chapter === 4 && (
          <p style={{ color: colors.mint, marginTop: 42, fontSize: 27, opacity: ramp(local, 65, 95) }}>{partB.video.end}</p>
        )}
      </div>

      <div style={{
        position: 'absolute', left: 105, right: 105, bottom: 55,
        borderTop: `1px solid ${colors.line}`, paddingTop: 25,
        display: 'flex', justifyContent: 'space-between', ...mono,
        fontSize: 15, color: colors.muted
      }}>
        <span>{partB.video.note}</span>
        <span>{content.s01.signal}</span>
      </div>
      <div style={{
        position: 'absolute', bottom: 0, left: 0, height: 3,
        width: '100%', background: colors.mint,
        transformOrigin: 'left',
        transform: `scaleX(${frame / 599})`
      }} />
    </AbsoluteFill>
  );
}
