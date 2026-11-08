/**
 * Changed: compose the Part C storyline, retain the existing hero/sonar scenes,
 * update navigation, and unmount the superseded sections without deleting them.
 */
import { useRef } from 'react';
import { useGSAP, refreshStory, setupLenis } from './lib/gsap';
import { content } from './content';
import { partC } from './content.partC';
import { Cursor } from './components/Cursor';
import { DepthGauge } from './components/DepthGauge';
import { SoundToggle } from './components/SoundToggle';
import { S01Hero } from './sections/S01Hero';
import { S02SideScan } from './sections/S02SideScan';
import { ProblemSection } from './sections/ProblemSection';
import { QuestionsSection } from './sections/QuestionsSection';
import { EightStagesSection } from './sections/EightStagesSection';
import { CompletenessSection } from './sections/CompletenessSection';
import { ValidationSection } from './sections/ValidationSection';
import { ContactSection } from './sections/ContactSection';
import { NextSection } from './sections/NextSection';
import { VideoSection } from './components/VideoSection';
import './styles.partC.css';

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
      <div ref={scope} className="dashboard-placeholder">
        <a className="back-link mono" href="/">← {content.ui.back}</a>
        <p className="eyebrow">{content.ui.pending}</p>
        <h1>{content.ui.dashboardTitle}</h1>
        <p className="body-copy">{content.ui.dashboardBody}</p>
        <div className="dashboard-grid">
          {content.ui.dashboardItems.map((item, i) => (
            <div key={item}><span className="mono">0{i + 1}</span><h2>{item}</h2></div>
          ))}
        </div>
        <p className="mono muted">{content.ui.dashboardStatus}</p>
      </div>
    );
  }

  return (
    <div ref={scope} className="site-root">
      <a className="skip-link" href="#story">{content.ui.skip}</a>
      <header className="site-header">
        <a href="#mission" className="wordmark" aria-label={content.ui.home}>
          <span className="brand-symbol" aria-hidden="true">⌁</span>
          {content.brand}<span className="brand-dot" />
        </a>
        <nav aria-label={content.ui.navLabel}>
          <a href="#problem">{partC.nav.problem}</a>
          <a href="#system">{partC.nav.system}</a>
          <a href="#honest-test">{partC.nav.evidence}</a>
        </nav>
        <SoundToggle />
      </header>
      <main id="story" tabIndex={-1}>
        <S01Hero />
        <ProblemSection />
        <S02SideScan />
        <QuestionsSection />
        <EightStagesSection />
        <CompletenessSection />
        <ValidationSection />
        <ContactSection />
        <VideoSection />
        <NextSection />
      </main>
      <DepthGauge />
      <Cursor />
      <div className="film-grain" aria-hidden="true" />
    </div>
  );
}
