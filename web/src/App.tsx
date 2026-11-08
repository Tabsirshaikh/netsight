import { lazy, Suspense, useRef } from 'react';
import { useGSAP, refreshStory, setupLenis } from './lib/gsap';
import { content } from './content';
import { Cursor } from './components/Cursor';
import { DepthGauge } from './components/DepthGauge';
import { SoundToggle } from './components/SoundToggle';
import { S01Hero } from './sections/S01Hero';
import { S02SideScan } from './sections/S02SideScan';
import { S03Pipeline } from './sections/S03Pipeline';
import { S04Reality } from './sections/S04Reality';
import { S05Detections } from './sections/S05Detections';
import { S06Trust } from './sections/S06Trust';
import { S07Geometry } from './sections/S07Geometry';
import { S08Curve } from './sections/S08Curve';
import { S09Ledger } from './sections/S09Ledger';
import { S10CTA } from './sections/S10CTA';
import { VideoSection } from './components/VideoSection';

const Dashboard = lazy(() => import('./dashboard/Dashboard'));

export default function App() {
  const scope = useRef<HTMLDivElement>(null);
  const dashboard = window.location.pathname.replace(/\/$/, '') === '/app';

  useGSAP(() => {
    if (dashboard) return;
    const teardown = setupLenis();
    let alive = true;
    const frame = requestAnimationFrame(refreshStory);
    document.fonts.ready.then(() => {
      if (alive) refreshStory();
    });
    const onLoad = () => refreshStory();
    window.addEventListener('load', onLoad);
    return () => {
      alive = false;
      cancelAnimationFrame(frame);
      window.removeEventListener('load', onLoad);
      teardown();
    };
  }, { scope, dependencies: [dashboard] });

  if (dashboard) {
    return (
      <Suspense fallback={
        <div role="status" style={{ background: '#030d14', color: '#e4eeec', minHeight: '100vh', padding: '3rem' }}>
          Opening NetSight research workspace…
        </div>
      }>
        <Dashboard />
      </Suspense>
    );
  }

  return (
    <div ref={scope} className="site-root">
      <a className="skip-link" href="#story">{content.ui.skip}</a>
      <header className="site-header">
        <a href="#mission" className="wordmark" aria-label={content.ui.home}>
          <span className="brand-symbol" aria-hidden="true">⌁</span>{content.brand}<span className="brand-dot" />
        </a>
        <nav aria-label={content.ui.navLabel}>
          <a href="#mission">{content.ui.mission}</a>
          <a href="#system">{content.ui.system}</a>
          <a href="#honest-test">{content.ui.validation}</a>
        </nav>
        <SoundToggle />
      </header>
      <main id="story" tabIndex={-1}>
        <S01Hero />
        <S02SideScan />
        <S03Pipeline />
        <S04Reality />
        <S05Detections />
        <S06Trust />
        <S07Geometry />
        <S08Curve />
        <S09Ledger />
        <VideoSection />
        <S10CTA />
      </main>
      <DepthGauge />
      <Cursor />
      <div className="film-grain" aria-hidden="true" />
    </div>
  );
}
