import { useRef, useState } from 'react';
import { refreshStory, useGSAP } from '../lib/gsap';

type Props = {
  file: string;
  className?: string;
};

/**
 * The procedural layer underneath is never removed.
 * Only mounts an <img> after an actual image response has been confirmed.
 * This also rejects Vite's HTML fallback for missing public files.
 * Files can be added to public/img without changing source code.
 */
export function OptionalAsset({ file, className = '' }: Props) {
  const scope = useRef<HTMLDivElement>(null);
  const [source, setSource] = useState<string | null>(null);

  useGSAP(() => {
    const abort = new AbortController();
    let alive = true;
    let requested = false;
    const url = `${import.meta.env.BASE_URL}img/${encodeURIComponent(file)}`;
    const observer = new IntersectionObserver(entries => {
      if (requested || !entries.some(entry => entry.isIntersecting)) return;
      requested = true;
      observer.disconnect();
      void fetch(url, {
        method: 'HEAD',
        signal: abort.signal,
        cache: 'force-cache'
      }).then(response => {
        if (
          alive && response.ok &&
          response.headers.get('content-type')?.startsWith('image/')
        ) setSource(url);
      }).catch(() => {
        // An absent optional asset is an expected, finished procedural state.
      });
    }, { rootMargin: '700px' });
    observer.observe(scope.current!);
    return () => {
      alive = false;
      abort.abort();
      observer.disconnect();
    };
  }, { scope, dependencies: [file] });

  return (
    <div ref={scope} className={`partb-asset ${className}`} aria-hidden="true">
      {source && (
        <img
          src={source}
          alt=""
          loading="lazy"
          decoding="async"
          onLoad={refreshStory}
          onError={() => setSource(null)}
        />
      )}
    </div>
  );
}
