import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { fileUrl, type Place } from './api';
import 'leaflet/dist/leaflet.css';

export function MapCanvas({ places, selected, enabled, onSelect }: {
  places: Place[]; selected: string | null; enabled: boolean; onSelect: (id: string) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  useEffect(() => {
    if (!element.current) return;
    const instance = L.map(element.current, { zoomControl: false, scrollWheelZoom: false }).setView([30, 0], 2);
    L.control.zoom({ position: 'topright' }).addTo(instance);
    instance.attributionControl.setPrefix(false);
    map.current = instance;
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(element.current);
    return () => { observer.disconnect(); instance.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    if (!map.current || !enabled) return;
    const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19, referrerPolicy: 'origin',
    }).addTo(map.current);
    return () => { layer.remove(); };
  }, [enabled]);
  useEffect(() => {
    if (!map.current) return;
    const markers = L.featureGroup().addTo(map.current);
    for (const place of places) {
      const content = document.createElement('div');
      content.className = 'memory-pin';
      const photo = document.createElement('img');
      photo.src = fileUrl(place.cover); photo.alt = ''; photo.loading = 'lazy';
      const count = document.createElement('span');
      count.textContent = String(place.count);
      content.append(photo, count);
      L.marker([place.latitude, place.longitude], {
        icon: L.divIcon({ html: content, className: 'memory-marker', iconSize: [54, 62], iconAnchor: [27, 62] }),
        title: place.name || `${place.latitude.toFixed(3)}, ${place.longitude.toFixed(3)}`,
        alt: `Ver lugar: ${place.name || place.id}`, keyboard: true,
      }).on('click', () => onSelect(place.id)).addTo(markers);
    }
    if (places.length) map.current.fitBounds(markers.getBounds(), { padding: [65, 65], maxZoom: 11, animate: false });
    return () => { markers.remove(); };
  }, [places, onSelect]);
  useEffect(() => {
    const place = places.find(item => item.id === selected);
    if (place && map.current) map.current.setView([place.latitude, place.longitude], 12, { animate: false });
  }, [selected, places]);
  return <div ref={element} className="places-map" role="region" aria-label="Mapa de tus recuerdos" />;
}
