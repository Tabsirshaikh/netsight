/**
 * SectionShell: semantic section + .section-stage pin target.
 * API: id, index, className, children; forwarded ref is the outer HTMLElement.
 * Pin only .section-stage, never the outer section. No triggers are created here.
 */
import { forwardRef, useImperativeHandle, useRef, type ReactNode } from 'react';
import { useGSAP } from '../lib/gsap';

type Props = {
  id: string;
  index: string;
  className?: string;
  children: ReactNode;
};

export const SectionShell = forwardRef<HTMLElement, Props>(function SectionShell(
  { id, index, className = '', children }, forwardedRef
) {
  const scope = useRef<HTMLElement>(null);
  useImperativeHandle(forwardedRef, () => scope.current!);
  useGSAP(() => {}, { scope });
  return (
    <section ref={scope} id={id} className={`story-section ${className}`} aria-labelledby={`${id}-title`} data-chapter={index}>
      <div className="section-stage">{children}</div>
    </section>
  );
});
