import { useEffect, useRef, useState } from 'react';
import * as L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Analysis, Ellipse95 } from './types';
import { percent } from './types';

/** Major axis is clockwise from north; the second axis is perpendicular. */
export function ellipsePoints(lat: number, lon: number, ellipse: Ellipse95): L.LatLngTuple[] {
  const [major, minor, orientation] = ellipse;
  const angle = orientation * Math.PI / 180;
  const cosLat = Math.cos(lat * Math.PI / 180);
  return Array.from({ length: 64 }, (_, i) => {
    const theta = i * Math.PI * 2 / 64;
    const a = major * Math.cos(theta);
    const b = minor * Math.sin(theta);
    const dn = a * Math.cos(angle) - b * Math.sin(angle);
    const de = a * Math.sin(angle) + b * Math.cos(angle);
    return [lat + dn / 111320, lon + de / (111320 * Math.max(1e-8, Math.abs(cosLat)))];
  });
}

export function ContactMap({ result, selected, onSelect }: {
  result: Analysis;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const select = useRef(onSelect);
  const markers = useRef(new Map<string, L.CircleMarker>());
  const [tilesFailed, setTilesFailed] = useState(false);
  useEffect(() => { select.current = onSelect; }, [onSelect]);

  useEffect(() => {
    if (!container.current) return;
    setTilesFailed(false);
    const map = L.map(container.current, { zoomAnimation: false, fadeAnimation: false, markerZoomAnimation: false }).setView([0, 0], 2);
    const tiles = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);
    const tileError = () => setTilesFailed(true);
    tiles.on('tileerror', tileError);
    const bounds = L.latLngBounds([]);
    const contacts = new Map(result.images.flatMap(image => image.detections.map(contact => [contact.id, contact] as const)));
    const keyboardCleanup: (() => void)[] = [];

    Object.entries(result.positions).forEach(([id, position]) => {
      const contact = contacts.get(id);
      if (!contact || !Number.isFinite(position.lat) || !Number.isFinite(position.lon)) return;
      const point: L.LatLngTuple = [position.lat, position.lon];
      const color = `hsl(${30 + contact.probability * 130}, 70%, 68%)`;
      if (position.ellipse95) {
        const points = ellipsePoints(position.lat, position.lon, position.ellipse95);
        L.polygon(points, { color, weight: 1, fillOpacity: 0.1, interactive: false }).addTo(map);
        points.forEach(p => bounds.extend(p));
      }
      const marker = L.circleMarker(point, { radius: 7, color, fillColor: color, fillOpacity: 0.8, weight: 2 }).addTo(map);
      const label = `${id} · calibrated probability ${percent(contact.probability)}`;
      const tooltip = document.createElement('span');
      tooltip.textContent = label;
      marker.bindTooltip(tooltip);
      marker.on('click', () => select.current(id));
      const element = marker.getElement() as HTMLElement | undefined;
      if (element) {
        element.setAttribute('tabindex', '0');
        element.setAttribute('role', 'button');
        element.setAttribute('aria-label', `Select ${label}`);
        const keydown = (event: KeyboardEvent) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            event.stopPropagation();
            select.current(id);
          }
        };
        element.addEventListener('keydown', keydown);
        keyboardCleanup.push(() => element.removeEventListener('keydown', keydown));
      }
      markers.current.set(id, marker);
      bounds.extend(point);
    });
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 17, animate: false });
    const observer = new ResizeObserver(() => map.invalidateSize({ animate: false }));
    observer.observe(container.current);
    return () => {
      observer.disconnect();
      keyboardCleanup.forEach(cleanup => cleanup());
      tiles.off('tileerror', tileError);
      markers.current.clear();
      map.remove();
    };
  }, [result]);

  useEffect(() => {
    markers.current.forEach((marker, id) => {
      marker.setRadius(id === selected ? 10 : 7);
      marker.setStyle({ weight: id === selected ? 4 : 2 });
      marker.getElement()?.setAttribute('aria-pressed', String(id === selected));
    });
  }, [selected, result]);

  return (
    <div className="ns-map-panel">
      <div ref={container} className="ns-contact-map" aria-label="Map of positioned contacts and 95% position ellipses" />
      {tilesFailed && <p className="ns-micro" role="status">Base map needs internet; positions and exports work offline</p>}
      {!Object.keys(result.positions).length && <p className="ns-muted">No positioned contacts in this saved run.</p>}
      <p className="ns-micro">Saved-run positions · colour by calibrated probability (warm = low, teal = high). Polygons show 95% position ellipses when available. Select a marker with click, Enter or Space.</p>
    </div>
  );
}
