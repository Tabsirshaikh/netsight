import { useRef } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';
import { ChapterPlaceholder } from '../components/ChapterPlaceholder';

export function S05Detections() {
  const scope = useRef<HTMLDivElement>(null);
  useGSAP(() => {}, { scope });
  return <div ref={scope}><ChapterPlaceholder data={content.s05} index="04" /></div>;
}
