import { useCallback, useEffect, useRef, useState } from 'react';
import { gsap, useGSAP } from '../lib/gsap';
import type { Completeness, CompletenessCell, Contact, SurveyImage } from './types';
import { cellDescription, percent } from './types';

interface Props {
  image: SurveyImage;
  url: string;
  flags: Set<string>;
  selected: string | null;
  onSelect: (id: string) => void;
  zoomRequest: number;
  completeness: Completeness | null;
}

export function Viewer({ image, url, flags, selected, onSelect, zoomRequest, completeness }: Props) {
  const root = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const mini = useRef<HTMLCanvasElement>(null);
  const transform = useRef({ x: 0, y: 0, scale: 1 });
  const size = useRef({ width: 1, height: 1 });
  const sweep = useRef({ progress: 1 });
  const drag = useRef<{ x: number; y: number; startX: number; startY: number; moved: boolean } | null>(null);
  const [bitmap, setBitmap] = useState<HTMLImageElement | null>(null);
  const [hover, setHover] = useState<{ contact: Contact; x: number; y: number } | null>(null);
  const [cellHover, setCellHover] = useState<{ cell: CompletenessCell; x: number; y: number } | null>(null);
  const [showCompleteness, setShowCompleteness] = useState(false);
  const [scaleLabel, setScaleLabel] = useState('100%');
  const [loadError, setLoadError] = useState(false);
  const tall = image.height > image.width * 2.5;

  const draw = useCallback(() => {
    const element = canvas.current;
    if (!element) return;
    const context = element.getContext('2d');
    if (!context) return;
    const { width, height } = size.current;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (element.width !== Math.round(width * dpr) || element.height !== Math.round(height * dpr)) {
      element.width = Math.round(width * dpr);
      element.height = Math.round(height * dpr);
    }
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, width, height);
    context.fillStyle = '#02090e';
    context.fillRect(0, 0, width, height);
    context.strokeStyle = '#10212a';
    context.lineWidth = 1;
    context.beginPath();
    for (let x = 0; x < width; x += 40) { context.moveTo(x, 0); context.lineTo(x, height); }
    for (let y = 0; y < height; y += 40) { context.moveTo(0, y); context.lineTo(width, y); }
    context.stroke();
    if (!bitmap) return;
    const { x, y, scale } = transform.current;
    context.save();
    context.translate(x, y);
    context.scale(scale, scale);
    context.drawImage(bitmap, 0, 0, image.width, image.height);
    context.restore();

    // Cell geometry uses exactly the image-to-screen transform used by boxes.
    if (showCompleteness && completeness?.available) {
      const styles = getComputedStyle(element);
      const low = styles.getPropertyValue('--ns-completeness-low').trim();
      const high = styles.getPropertyValue('--ns-completeness-high').trim();
      const hatch = styles.getPropertyValue('--ns-completeness-hatch').trim();
      completeness.cells.filter(cell => cell.image_index === image.index).forEach(cell => {
        const [x0, y0, x1, y1] = cell.box;
        const bx = x + x0 * scale;
        const by = y + y0 * scale;
        const bw = (x1 - x0) * scale;
        const bh = (y1 - y0) * scale;
        context.save();
        context.beginPath();
        context.rect(bx, by, bw, bh);
        context.clip();
        // Two alpha-composited endpoints keep the scale driven by CSS variables.
        // Cells with too few trials have no estimate: hatch only, never a Pd colour.
        if (cell.status !== 'insufficient_trials') {
          const t = Math.max(0, Math.min(1, cell.pd_lower));
          context.globalAlpha = 0.36;
          context.fillStyle = low;
          context.fillRect(bx, by, bw, bh);
          context.globalAlpha = t * 0.75;
          context.fillStyle = high;
          context.fillRect(bx, by, bw, bh);
        }
        context.globalAlpha = 0.65;
        context.strokeStyle = hatch;
        context.lineWidth = 1;
        if (cell.status === 'insufficient_trials') {
          context.beginPath();
          const left = Math.max(0, bx);
          const top = Math.max(0, by);
          const right = Math.min(width, bx + bw);
          const bottom = Math.min(height, by + bh);
          for (let start = left - (bottom - top); start < right; start += 9) {
            context.moveTo(start, bottom);
            context.lineTo(start + (bottom - top), top);
          }
          context.stroke();
          context.globalAlpha = 1;
          context.font = '10px "IBM Plex Mono", monospace';
          context.fillStyle = '#04131e';
          context.fillRect(bx + 3, by + 3, 94, 17);
          context.fillStyle = hatch;
          context.fillText('too few trials', bx + 6, by + 15);
        }
        context.restore();
        context.save();
        context.strokeStyle = hatch;
        context.globalAlpha = 0.3;
        context.lineWidth = 1;
        context.strokeRect(bx, by, bw, bh);
        context.restore();
      });
    }

    image.detections.forEach((contact, index) => {
      const reveal = Math.max(0, Math.min(1, sweep.current.progress * 1.3 - index / Math.max(1, image.detections.length) * 0.3));
      if (!reveal) return;
      const [x1, y1, x2, y2] = contact.box;
      const bx = x + x1 * scale;
      const by = y + y1 * scale;
      const bw = (x2 - x1) * scale;
      const bh = (y2 - y1) * scale;
      const flagged = flags.has(contact.id);
      const active = selected === contact.id;
      const hue = 30 + contact.probability * 130;
      context.save();
      context.globalAlpha = reveal * (active ? 1 : flagged ? 0.65 + contact.probability * 0.35 : 0.3);
      context.strokeStyle = active ? '#ffffff' : `hsl(${hue}, 70%, 68%)`;
      context.fillStyle = `hsla(${hue}, 70%, 65%, ${active ? 0.2 : 0.07})`;
      context.lineWidth = active ? 2 : 1.5;
      context.setLineDash(flagged ? [] : [4, 4]);
      context.fillRect(bx, by, bw, bh);
      context.strokeRect(bx, by, bw, bh);
      if (flagged || active) {
        const label = `${contact.id} · ${percent(contact.probability)}`;
        context.font = '10px "IBM Plex Mono", monospace';
        const textWidth = context.measureText(label).width + 10;
        const labelY = Math.max(0, by - 19);
        context.fillStyle = '#04131e';
        context.fillRect(bx, labelY, textWidth, 18);
        context.fillStyle = active ? '#fff' : '#bcebdc';
        context.fillText(label, bx + 5, labelY + 12);
      }
      context.restore();
    });

    if (tall && mini.current) {
      const m = mini.current;
      const c = m.getContext('2d');
      if (c) {
        c.clearRect(0, 0, m.width, m.height);
        c.drawImage(bitmap, 0, 0, m.width, m.height);
        c.fillStyle = 'rgba(109,226,195,.16)';
        c.strokeStyle = '#6de2c3';
        c.lineWidth = 2;
        const vx = -x / scale / image.width * m.width;
        const vy = -y / scale / image.height * m.height;
        const vw = width / scale / image.width * m.width;
        const vh = height / scale / image.height * m.height;
        c.fillRect(vx, vy, vw, vh);
        c.strokeRect(vx, vy, vw, vh);
      }
    }
    setScaleLabel(`${Math.round(scale * 100)}%`);
  }, [bitmap, image, flags, selected, tall, showCompleteness, completeness]);

  const fit = useCallback(() => {
    const { width, height } = size.current;
    const scale = Math.max(0.002, Math.min((width - 56) / image.width, (height - 56) / image.height));
    transform.current = {
      x: (width - image.width * scale) / 2,
      y: (height - image.height * scale) / 2,
      scale,
    };
    draw();
  }, [image.width, image.height, draw]);

  useEffect(() => {
    setBitmap(null);
    setHover(null);
    setCellHover(null);
    setLoadError(false);
    const img = new Image();
    let alive = true;
    img.onload = () => { if (alive) setBitmap(img); };
    img.onerror = () => { if (alive) setLoadError(true); };
    img.src = url;
    return () => { alive = false; img.onload = null; img.onerror = null; };
  }, [url]);

  useEffect(() => {
    if (!root.current) return;
    const observer = new ResizeObserver(entries => {
      const rect = entries[0].contentRect;
      size.current = { width: rect.width, height: rect.height };
      draw();
    });
    observer.observe(root.current);
    return () => observer.disconnect();
  }, [draw]);

  useEffect(() => { if (bitmap) fit(); }, [bitmap, image.width, image.height]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { draw(); }, [draw]);

  useGSAP(() => {
    if (!bitmap) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      sweep.current.progress = 1;
      draw();
      return;
    }
    sweep.current.progress = 0;
    gsap.to(sweep.current, { progress: 1, duration: 0.8, ease: 'power2.out', onUpdate: draw });
  }, { scope: root, dependencies: [bitmap], revertOnUpdate: true });

  const zoomAt = useCallback((factor: number, x: number, y: number) => {
    const old = transform.current;
    const scale = Math.max(0.002, Math.min(32, old.scale * factor));
    const ratio = scale / old.scale;
    transform.current = { scale, x: x - (x - old.x) * ratio, y: y - (y - old.y) * ratio };
    setCellHover(null);
    draw();
  }, [draw]);

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const wheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = element.getBoundingClientRect();
      zoomAt(Math.exp(-event.deltaY * 0.0015), event.clientX - rect.left, event.clientY - rect.top);
    };
    element.addEventListener('wheel', wheel, { passive: false });
    return () => element.removeEventListener('wheel', wheel);
  }, [zoomAt]);

  useEffect(() => {
    if (!zoomRequest) return;
    const contact = image.detections.find(d => d.id === selected);
    if (!contact) return;
    const [x1, y1, x2, y2] = contact.box;
    const { width, height } = size.current;
    const scale = Math.min(16, width / Math.max(80, (x2 - x1) * 3), height / Math.max(80, (y2 - y1) * 3));
    transform.current = {
      scale,
      x: width / 2 - (x1 + x2) / 2 * scale,
      y: height / 2 - (y1 + y2) / 2 * scale,
    };
    draw();
  }, [zoomRequest]); // eslint-disable-line react-hooks/exhaustive-deps

  function hit(x: number, y: number) {
    const t = transform.current;
    const px = (x - t.x) / t.scale;
    const py = (y - t.y) / t.scale;
    return [...image.detections].reverse().find(d =>
      px >= d.box[0] && px <= d.box[2] && py >= d.box[1] && py <= d.box[3]);
  }

  function hitCell(x: number, y: number) {
    if (!showCompleteness || !completeness?.available) return;
    const t = transform.current;
    const px = (x - t.x) / t.scale;
    const py = (y - t.y) / t.scale;
    return completeness.cells.find(c => c.image_index === image.index &&
      px >= c.box[0] && px < c.box[2] && py >= c.box[1] && py < c.box[3]);
  }

  return (
    <div className="ns-viewer" ref={root}>
      <canvas ref={canvas} className="ns-main-canvas" tabIndex={0}
        aria-label={`Sonar viewer: ${image.name}. Drag to pan, scroll to zoom. Select contacts in the inspector for keyboard access. Completeness cell measurements are available in the Search completeness grids. Press zero to fit.`}
        onKeyDown={event => {
          if (event.key === '0') { event.preventDefault(); fit(); }
          if (event.key === '+' || event.key === '=') zoomAt(1.3, size.current.width / 2, size.current.height / 2);
          if (event.key === '-') zoomAt(1 / 1.3, size.current.width / 2, size.current.height / 2);
        }}
        onPointerDown={event => {
          event.currentTarget.focus();
          event.currentTarget.setPointerCapture(event.pointerId);
          drag.current = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: false };
        }}
        onPointerMove={event => {
          const rect = event.currentTarget.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          if (drag.current) {
            const d = drag.current;
            if (Math.hypot(event.clientX - d.startX, event.clientY - d.startY) > 3) d.moved = true;
            transform.current.x += event.clientX - d.x;
            transform.current.y += event.clientY - d.y;
            d.x = event.clientX;
            d.y = event.clientY;
            setHover(null);
            setCellHover(null);
            draw();
          } else {
            const contact = hit(x, y);
            const cell = hitCell(x, y);
            setHover(contact ? { contact, x, y } : null);
            setCellHover(cell ? { cell, x, y } : null);
          }
        }}
        onPointerUp={event => {
          const rect = event.currentTarget.getBoundingClientRect();
          if (drag.current && !drag.current.moved) {
            const contact = hit(event.clientX - rect.left, event.clientY - rect.top);
            if (contact) onSelect(contact.id);
          }
          drag.current = null;
          event.currentTarget.releasePointerCapture(event.pointerId);
        }}
        onPointerCancel={() => { drag.current = null; }}
        onPointerLeave={() => { setHover(null); setCellHover(null); }}
      />
      <div className="ns-viewer-label"><span className="ns-live-dot" /> SONAR / {image.width} × {image.height} PX</div>
      <div className="ns-viewer-tools">
        {completeness?.available && <button aria-pressed={showCompleteness} onClick={() => { setShowCompleteness(v => !v); setCellHover(null); }}>Completeness</button>}
        <button onClick={fit} title="Fit image (0)">Fit <kbd>0</kbd></button>
        <button onClick={() => zoomAt(1 / 1.4, size.current.width / 2, size.current.height / 2)} aria-label="Zoom out">−</button>
        <span>{scaleLabel}</span>
        <button onClick={() => zoomAt(1.4, size.current.width / 2, size.current.height / 2)} aria-label="Zoom in">+</button>
      </div>
      <div className="ns-viewer-legend">
        <i /> Flagged <i className="unflagged" /> Below threshold
        {showCompleteness && completeness?.available && <div className="ns-completeness-legend">Pd lower90: 0 <b /> 1 · <em /> too few trials</div>}
      </div>
      {(hover || (cellHover && showCompleteness)) && (
        <div className="ns-tooltip" style={{
          left: Math.max(8, Math.min((hover?.x ?? cellHover?.x ?? 0) + 14, size.current.width - 220)),
          top: Math.max(8, Math.min((hover?.y ?? cellHover?.y ?? 0) + 14, size.current.height - 130)),
        }}>
          {hover && <>
            <strong>{hover.contact.id} · {percent(hover.contact.probability)}</strong>
            <span>Calibrated on validation surveys</span>
            <span>{flags.has(hover.contact.id) ? 'Flagged for review' : 'Below operating threshold'} · click to inspect</span>
          </>}
          {cellHover && showCompleteness && <span>{cellDescription(cellHover.cell)}</span>}
        </div>
      )}
      {tall && (
        <button className="ns-minimap" aria-label="Waterfall minimap: click to centre the viewport"
          onClick={event => {
            const rect = event.currentTarget.getBoundingClientRect();
            const py = (event.clientY - rect.top) / rect.height * image.height;
            transform.current.y = size.current.height / 2 - py * transform.current.scale;
            draw();
          }}>
          <canvas ref={mini} width={64} height={180} /><span>OVERVIEW</span>
        </button>
      )}
      {loadError && <p className="ns-image-error" role="alert">Preview could not be loaded. Re-run the survey or check the API connection.</p>}
    </div>
  );
}
