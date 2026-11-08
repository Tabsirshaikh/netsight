import { useRef } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';
import { ChapterPlaceholder } from '../components/ChapterPlaceholder';

export function S08Curve() {
  const scope = useRef<HTMLDivElement>(null);
  useGSAP(() => {}, { scope });
  return <div ref={scope}><ChapterPlaceholder data={content.s08} index="07" /></div>;
}
