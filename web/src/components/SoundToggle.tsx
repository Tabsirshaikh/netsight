/**
 * SoundToggle API: mount once. OFF initially; AudioContext is created only on click.
 * Synthesised ping is an illustrative cue, not survey audio. Closes on unmount.
 */
import { useRef, useState } from 'react';
import { useGSAP } from '../lib/gsap';
import { content } from '../content';

export function SoundToggle() {
  const scope = useRef<HTMLButtonElement>(null);
  const context = useRef<AudioContext | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [enabled, setEnabled] = useState(false);

  const stop = () => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    void context.current?.close();
    context.current = null;
  };

  useGSAP(() => () => stop(), { scope });

  async function toggle() {
    if (enabled) {
      stop();
      setEnabled(false);
      return;
    }
    if (!window.AudioContext) return;
    try {
      const audio = new AudioContext();
      context.current = audio;
      await audio.resume();
      if (context.current !== audio) return;
      const ping = () => {
        if (document.hidden || audio.state !== 'running') return;
        const oscillator = audio.createOscillator();
        const gain = audio.createGain();
        const now = audio.currentTime;
        oscillator.frequency.setValueAtTime(740, now);
        oscillator.frequency.exponentialRampToValueAtTime(510, now + 0.5);
        gain.gain.setValueAtTime(0, now);
        gain.gain.linearRampToValueAtTime(0.025, now + 0.015);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.75);
        oscillator.connect(gain).connect(audio.destination);
        oscillator.start(now);
        oscillator.stop(now + 0.8);
        oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
      };
      ping();
      timer.current = setInterval(ping, 3600);
      setEnabled(true);
    } catch {
      stop();
      setEnabled(false);
    }
  }

  return (
    <button ref={scope} className="sound-toggle" type="button" onClick={toggle}
      aria-label={content.ui.soundLabel} aria-pressed={enabled}>
      <span className={`sound-bars ${enabled ? 'on' : ''}`} aria-hidden="true"><i /><i /><i /></span>
      <span>{enabled ? content.ui.soundOn : content.ui.soundOff}</span>
    </button>
  );
}
