import { useRef } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';
import { ChapterPlaceholder } from '../components/ChapterPlaceholder';

export function S06Trust() {
  const scope = useRef<HTMLDivElement>(null);
  useGSAP(() => {}, { scope });
  return <div ref={scope}><ChapterPlaceholder data={content.s06} index="05" /></div>;
}
