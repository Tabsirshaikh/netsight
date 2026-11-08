/**
 * Part A placeholder API: data {id, eyebrow, title, intro, notes}, index.
 * No pinning or canvas allocation. Replace the calling S05–S09 component in Part B.
 * Facts remain accessible rather than being hidden behind unfinished animations.
 */
import { useRef } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';
import { Badge } from './Badge';

type ChapterData = {
  id: string;
  eyebrow: string;
  title: string;
  intro: string;
  notes: readonly string[];
};

export function ChapterPlaceholder({ data, index }: { data: ChapterData; index: string }) {
  const scope = useRef<HTMLElement>(null);
  useGSAP(() => {}, { scope });
  return (
    <section ref={scope} id={data.id} className="chapter-placeholder" aria-labelledby={`${data.id}-title`}>
      <div className="placeholder-number" aria-hidden="true">{index}</div>
      <div className="placeholder-content">
        <p className="eyebrow">{data.eyebrow}</p>
        <h2 id={`${data.id}-title`}>{data.title}</h2>
        <p className="body-copy">{data.intro}</p>
        <div className="placeholder-meta"><Badge /><span className="mono">{content.ui.placeholder}</span></div>
        <details>
          <summary>{content.ui.expandNotes}<span aria-hidden="true">+</span></summary>
          <ul>{data.notes.map(note => <li key={note}>{note}</li>)}</ul>
        </details>
      </div>
    </section>
  );
}
