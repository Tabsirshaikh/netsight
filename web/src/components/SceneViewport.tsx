/**
 * SceneViewport API: kind + mutable progress ref, optional className/label.
 * Loads the entire WebGL engine only within 700px of the viewport.
 * Render loops pause when offscreen; no scene state lives in React per frame.
 * All visual geometry has a CSS fallback. Canvas is decorative; label is exposed once.
 */
import { Component, Suspense, lazy, useRef, useState, type ReactNode } from 'react';
import { useGSAP, type Progress } from '../lib/gsap';
import { content } from '../content';

export type SceneKind = 'hero' | 'sonar' | 'pipeline' | 'comparison' | 'beacon';
export type SceneProps = { kind: SceneKind; progress: Progress; active: boolean };
const SceneRoot = lazy(() => import('../three/SceneRoot'));

class CanvasBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    return this.state.failed
      ? <span className="sr-only">{content.ui.canvasFallback}</span>
      : this.props.children;
  }
}

export function SceneViewport({ kind, progress, className = '', label }: {
  kind: SceneKind;
  progress: Progress;
  className?: string;
  label: string;
}) {
  const scope = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [active, setActive] = useState(false);
  useGSAP(() => {
    const loadObserver = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setReady(true);
        loadObserver.disconnect();
      }
    }, { rootMargin: '700px' });
    const playObserver = new IntersectionObserver(entries => {
      setActive(entries.some(entry => entry.isIntersecting));
    }, { rootMargin: '100px' });
    loadObserver.observe(scope.current!);
    playObserver.observe(scope.current!);
    return () => { loadObserver.disconnect(); playObserver.disconnect(); };
  }, { scope });
  return (
    <div ref={scope} className={`scene-viewport scene-${kind} ${className}`} role="img" aria-label={label}>
      <div className="scene-fallback" aria-hidden="true">
        <div className="fallback-ring ring-one" /><div className="fallback-ring ring-two" />
        <div className="fallback-grid" />
        {kind === 'sonar' && <div className="fallback-waterfall"><i /><b /></div>}
        {kind === 'pipeline' && <div className="fallback-stack">{Array.from({ length: 6 }, (_, i) => <i key={i} />)}</div>}
        {kind === 'comparison' && <div className="fallback-columns"><i /><i /><i /></div>}
      </div>
      {ready && (
        <CanvasBoundary>
          <Suspense fallback={null}>
            <SceneRoot kind={kind} progress={progress} active={active} />
          </Suspense>
        </CanvasBoundary>
      )}
    </div>
  );
}
