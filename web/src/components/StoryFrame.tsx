/**
 * Part C animation boundary. Text remains semantic and readable without motion.
 * Only the compact desktop map is pinned; long sections retain natural flow.
 */
import { useRef, type ReactNode } from 'react';
import { gsap, useGSAP, motionQuery, reduceQuery } from '../lib/gsap';

type Props = {
  id: string;
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
  className?: string;
  pin?: boolean;
};

export function StoryFrame({
  id, eyebrow, title, intro, children, className = '', pin = false
}: Props) {
  const scope = useRef<HTMLElement>(null);

  useGSAP(() => {
    const root = scope.current;
    if (!root) return;
    const media = gsap.matchMedia();

    media.add(reduceQuery, () => {
      gsap.set('.c-reveal, .c-layer, .c-gap, .c-swath', {
        autoAlpha: 1, clearProps: 'transform'
      });
      gsap.set('.c-draw', { drawSVG: '0% 100%' });
    });

    media.add(motionQuery, () => {
      const stage = root.querySelector<HTMLElement>('.c-stage');
      const canPin = pin &&
        window.matchMedia('(min-width: 1100px) and (min-height: 850px)').matches &&
        !!stage && stage.scrollHeight <= window.innerHeight;

      const timeline = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: {
          trigger: root,
          start: canPin ? 'top top' : 'top 82%',
          end: canPin ? '+=140%' : 'bottom 90%',
          pin: canPin ? stage : false,
          scrub: 0.65,
          anticipatePin: 1,
          invalidateOnRefresh: true
        }
      });

      timeline
        .from('.c-reveal', {
          y: 28, autoAlpha: 0.15, duration: 0.3, stagger: 0.035
        }, 0)
        .from('.c-layer', {
          y: (i: number) => -i * 10,
          x: -18,
          autoAlpha: 0.2,
          rotationX: 12,
          duration: 0.38,
          stagger: 0.045
        }, 0.06);

      if (root.querySelector('.c-draw')) {
        timeline.from('.c-draw', { drawSVG: '0% 0%', duration: 0.5 }, 0.12);
      }
      if (root.querySelector('.c-swath')) {
        timeline.from('.c-swath', {
          scaleY: 0, transformOrigin: '50% 0%',
          duration: 0.3, stagger: 0.035
        }, 0);
      }
      if (root.querySelector('.c-gap')) {
        timeline.from('.c-gap', {
          autoAlpha: 0, duration: 0.3, stagger: 0.04
        }, 0.55);
      }
    });

    return () => media.revert();
  }, { scope, dependencies: [pin] });

  return (
    <section
      ref={scope}
      id={id}
      className={`c-section story-section ${className}`}
      aria-labelledby={`${id}-title`}
    >
      <div className="c-stage">
        <header className="c-heading c-reveal">
          <p className="c-eyebrow">{eyebrow}</p>
          <h2 id={`${id}-title`}>{title}</h2>
          <p className="c-intro">{intro}</p>
        </header>
        {children}
      </div>
    </section>
  );
}
