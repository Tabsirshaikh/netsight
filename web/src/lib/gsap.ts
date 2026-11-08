/**
 * The only plugin-registration module.
 * Import gsap/useGSAP/plugins from here, not from individual GSAP packages.
 * setupLenis() returns an idempotent teardown; call once in the application shell.
 */
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import { Flip } from 'gsap/Flip';
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin';
import { useGSAP } from '@gsap/react';
import Lenis from 'lenis';

gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText, Flip, DrawSVGPlugin);

export { gsap, ScrollTrigger, SplitText, Flip, DrawSVGPlugin, useGSAP };

export type Progress = { current: number };
export const motionQuery = '(prefers-reduced-motion: no-preference)';
export const reduceQuery = '(prefers-reduced-motion: reduce)';

export function setupLenis() {
  const media = gsap.matchMedia();
  media.add(motionQuery, () => {
    const lenis = new Lenis({
      autoRaf: false,
      anchors: true,
      smoothWheel: true,
      syncTouch: false,
      duration: 1.15
    });
    const update = () => ScrollTrigger.update();
    const tick = (seconds: number) => lenis.raf(seconds * 1000);
    lenis.on('scroll', update);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(tick);
      lenis.off('scroll', update);
      lenis.destroy();
    };
  });
  return () => media.revert();
}

export function refreshStory() {
  ScrollTrigger.sort();
  ScrollTrigger.refresh();
}
