import { useId, useRef } from 'react';
import { useGSAP } from '../lib/gsap';
import { OptionalAsset } from './OptionalAsset';

export type SonarVariant = 'wreck' | 'person' | 'pot' | 'contact' | 'mine';

type Props = {
  variant: SonarVariant;
  label: string;
  file?: string;
  className?: string;
  geometry?: boolean;
};

/**
 * Deterministic, lightweight vector sonar illustration.
 * Bright structure, adjacent dark shadow, central nadir and horizontal returns
 * explain the instrument; no photograph or measured detection is implied.
 */
export function SonarArtwork({
  variant, label, file, className = '', geometry = false
}: Props) {
  const scope = useRef<HTMLDivElement>(null);
  const id = useId().replace(/:/g, '');
  useGSAP(() => {}, { scope });

  return (
    <div ref={scope} className={`partb-sonar ${className}`} role="img" aria-label={label}>
      {file && <OptionalAsset file={file} />}
      <svg viewBox="0 0 400 400" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id={`${id}-bed`} x2="1" y2=".25">
            <stop stopColor="#0a2226" />
            <stop offset=".45" stopColor="#34574a" stopOpacity=".75" />
            <stop offset="1" stopColor="#0a2025" />
          </linearGradient>
          <pattern id={`${id}-mesh`} width="9" height="9" patternUnits="userSpaceOnUse">
            <path d="M0 0H9V9" fill="none" stroke="#d3dbc0" strokeWidth="1" />
          </pattern>
          <pattern id={`${id}-lines`} width="400" height="5" patternUnits="userSpaceOnUse">
            <path d="M0 1H400" stroke="#9fbba0" strokeOpacity=".11" />
            <path d="M0 3H400" stroke="#020e14" strokeOpacity=".27" />
          </pattern>
          <clipPath id={`${id}-clip`}><rect width="400" height="400" /></clipPath>
        </defs>
        <g clipPath={`url(#${id}-clip)`}>
          <rect width="400" height="400" fill={`url(#${id}-bed)`} fillOpacity=".83" />
          {Array.from({ length: 38 }, (_, i) => {
            const y = i * 12 - 20;
            const offset = Math.sin(i * 1.7) * 8;
            return (
              <path
                key={i}
                d={`M-20 ${y} Q100 ${y + 32 + offset} 220 ${y + 12} T430 ${y + 35}`}
                fill="none"
                stroke={i % 3 === 0 ? '#adc9a1' : '#729d87'}
                strokeWidth={i % 4 === 0 ? 2 : .7}
                opacity={.12 + (i % 5) * .025}
              />
            );
          })}
          {Array.from({ length: 90 }, (_, i) => (
            <rect
              key={i}
              x={(i * 137 + 23) % 400}
              y={(i * 79 + 41) % 400}
              width={i % 3 === 0 ? 3 : 1}
              height="1"
              fill="#d4d9ac"
              opacity={.12 + (i % 4) * .07}
            />
          ))}
          <rect x="35" width="17" height="400" fill="#020c13" opacity=".91" />
          <path d="M34 0V400M53 0V400" stroke="#89b297" strokeOpacity=".24" />

          <g className={geometry ? 'geometry-object' : undefined}>
            {variant === 'wreck' && (
              <g transform="translate(214 204) rotate(-23)">
                <path d="M-46-98L35-96 92 68 43 115-8 91Z" fill="#020c13" opacity=".9" />
                <path d="M-43-103Q10-127 38-66L45 66Q19 120-20 91L-45 24Z" fill="#687d67" stroke="#d0d7b3" strokeWidth="3" />
                <path d="M-34-73L31-56M-39-45L38-28M-40-16L42 0M-37 13L43 30M-30 43L36 58M-20 73L20 84M-2-101L11 92" stroke="#d7d9b6" strokeWidth="2" />
                <path d="M-18-64L15-57 20 1-14-6Z" fill="#122a28" stroke="#abb897" />
              </g>
            )}
            {variant === 'person' && (
              <g transform="translate(222 210) rotate(20)">
                <path d="M13-42Q60-40 65-13L91 38 75 43 49 15 55 74 37 76 22 20 11 52-4 44 12 5Z" fill="#020c13" />
                <circle cy="-48" r="12" fill="#c1c9a1" />
                <path d="M-11-30L12-29 18 13 29 61 18 64 1 24-13 65-24 60-12 11-33 21-38 12-17-13Z" fill="#abbc98" stroke="#e4dfb9" strokeWidth="2" />
              </g>
            )}
            {(variant === 'pot' || variant === 'contact') && (
              <g transform={`translate(222 205) rotate(${variant === 'contact' ? 14 : -17})`}>
                <path d="M-52-52H41L114-13 97 90 15 61Z" fill="#020c13" opacity=".96" />
                <path d="M-60-51L28-64 54-31 43 52-46 65-64 33Z" fill={`url(#${id}-mesh)`} stroke="#d6dbb7" strokeWidth="3" />
                <path d="M-60-51L-39-23 54-31M-39-23L-46 65M28-64L13-25 10 56M-64 33L43 20" fill="none" stroke="#c5d0ae" strokeWidth="2" />
                <ellipse cx="-2" cy="5" rx="15" ry="20" fill="#10201d" stroke="#c9d2af" strokeWidth="2" />
                <path d="M-60-51Q-108-94-110-146" fill="none" stroke="#b8c3a1" strokeWidth="1.5" />
              </g>
            )}
            {variant === 'mine' && (
              <g transform="translate(215 207) rotate(-12)">
                <path d="M-10-33Q79-53 126-20L110 54Q36 60-14 25Z" fill="#020c13" />
                <ellipse rx="40" ry="31" fill="#95a485" stroke="#d9d9b5" strokeWidth="3" />
                <path d="M-23-24Q-4-38 16-28M-36-5Q-4 9 35-4" fill="none" stroke="#e1dec0" strokeWidth="3" />
                <path d="M-15 10Q0 23 25 10" fill="none" stroke="#374c40" strokeWidth="4" />
              </g>
            )}
          </g>

          <rect width="400" height="400" fill={`url(#${id}-lines)`} />
          <g className="detection-box" fill="none" stroke="#8ef3cc" strokeWidth="1.4">
            <path d="M131 92H307V322H131Z" />
            <path d="M131 109V92H148M290 92H307V109M307 305V322H290M148 322H131V305" strokeWidth="3" />
          </g>
          <g className="sonar-sweep" opacity=".6">
            <path d="M0 64H400" stroke="#a0f5d6" strokeWidth="1" />
            <path d="M0 60H400" stroke="#a0f5d6" strokeWidth="5" opacity=".08" />
          </g>
        </g>
      </svg>
    </div>
  );
}
