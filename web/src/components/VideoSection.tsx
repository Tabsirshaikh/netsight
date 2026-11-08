/** Two videos: a short muted explainer loop and the full overview (click to play, not preloaded). */
export function VideoSection() {
  return (
    <section id="videos" aria-labelledby="videos-title" className="relative mx-auto max-w-6xl px-4 py-24">
      <h2 id="videos-title" className="mb-8 text-3xl font-semibold tracking-tight text-white md:text-5xl">
        See it in motion
      </h2>
      <div className="grid gap-8 md:grid-cols-2">
        <figure>
          <video className="w-full rounded-xl border border-white/10" src="/video/explainer.mp4"
            autoPlay muted loop playsInline preload="metadata" aria-label="20-second NetSight explainer" />
          <figcaption className="mt-3 text-sm text-white/60">20-second explainer: ping, image, detections, trust level, evidence pack.</figcaption>
        </figure>
        <figure>
          <video className="w-full rounded-xl border border-white/10" src="/video/netsight-overview.mp4"
            controls playsInline preload="none" aria-label="NetSight full overview video" />
          <figcaption className="mt-3 text-sm text-white/60">Full overview (8 min, with sound). Click to play.</figcaption>
        </figure>
      </div>
    </section>
  );
}
