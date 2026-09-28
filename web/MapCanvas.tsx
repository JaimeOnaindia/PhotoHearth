import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { fileUrl, type Place } from './api';
import 'leaflet/dist/leaflet.css';

export type MapPoint = { latitude: number; longitude: number };

export function MapCanvas({ places, selected, enabled, onSelect, draft, picking, onPick }: {
  places: Place[]; selected: string | null; enabled: boolean; onSelect: (id: string) => void;
  draft?: MapPoint | null; picking?: boolean; onPick?: (latitude: number, longitude: number) => void;
}) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const markerPhotos = useRef<HTMLImageElement[]>([]);
  const tilesReady = useRef(false);
  const [tileStatus, setTileStatus] = useState<'loading' | 'ready' | 'error'>('loading');
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
    const place = places.find(item => item.id === selected);
    if (place) map.current.setView([place.latitude, place.longitude], 12, { animate: false });
    else if (places.length) map.current.fitBounds(
      L.latLngBounds(places.map(item => [item.latitude, item.longitude])),
      { padding: [65, 65], maxZoom: 11, animate: false },
    );
  }, [places, selected, enabled]);
  useEffect(() => {
    if (!map.current || !enabled) return;
    tilesReady.current = false;
    setTileStatus('loading');
    let loaded = false;
    const showTile = () => { loaded = true; setTileStatus('ready'); };
    const finishTiles = () => {
      tilesReady.current = true;
      for (const photo of markerPhotos.current) {
        if (photo.dataset.src) {
          photo.src = photo.dataset.src;
          delete photo.dataset.src;
        }
      }
      if (!loaded) setTileStatus('error');
    };
    const layer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19, referrerPolicy: 'origin',
    }).on('tileload', showTile).on('load', finishTiles).addTo(map.current);
    return () => { layer.off('tileload', showTile).off('load', finishTiles).remove(); tilesReady.current = false; };
  }, [enabled]);
  useEffect(() => {
    if (!map.current || !enabled) return;
    const markers = L.featureGroup().addTo(map.current);
    const photos: HTMLImageElement[] = [];
    markerPhotos.current = photos;
    for (const place of places) {
      const content = document.createElement('div');
      content.className = 'memory-pin';
      const photo = document.createElement('img');
      const src = fileUrl(place.cover);
      if (tilesReady.current) photo.src = src;
      else { photo.dataset.src = src; photos.push(photo); }
      photo.alt = ''; photo.loading = 'lazy';
      const count = document.createElement('span');
      count.textContent = String(place.count);
      content.append(photo, count);
      L.marker([place.latitude, place.longitude], {
        icon: L.divIcon({ html: content, className: 'memory-marker', iconSize: [54, 62], iconAnchor: [27, 62] }),
        title: place.name || `${place.latitude.toFixed(3)}, ${place.longitude.toFixed(3)}`,
        alt: `Ver lugar: ${place.name || place.id}`, keyboard: true,
      }).on('click', () => {
        if (picking && onPick) onPick(place.latitude, place.longitude);
        else onSelect(place.id);
      }).addTo(markers);
    }
    return () => { markers.remove(); markerPhotos.current = []; };
  }, [places, enabled, onSelect, onPick, picking]);
  useEffect(() => {
    if (!map.current || !onPick) return;
    const instance = map.current;
    const handle = (event: L.LeafletMouseEvent) => onPick(
      Number(event.latlng.lat.toFixed(6)),
      Number(event.latlng.lng.toFixed(6)),
    );
    instance.on('click', handle);
    return () => { instance.off('click', handle); };
  }, [onPick]);
  useEffect(() => {
    if (!map.current || !draft) return;
    const marker = L.marker([draft.latitude, draft.longitude], {
      icon: L.divIcon({ html: '<span></span>', className: 'draft-marker', iconSize: [30, 38], iconAnchor: [15, 38] }),
      title: 'Nueva ubicación', keyboard: false,
    }).addTo(map.current);
    return () => { marker.remove(); };
  }, [draft]);
  return <>
    <div ref={element} className={`places-map ${picking ? 'is-picking' : ''}`} role="region" aria-label={picking ? 'Elige una ubicación en el mapa' : 'Mapa de tus recuerdos'} />
    {enabled && tileStatus !== 'ready' && <span className="map-tile-status" role={tileStatus === 'error' ? 'alert' : 'status'}>{tileStatus === 'error' ? 'No se pudo cargar el mapa base. Comprueba la conexión.' : 'Cargando mapa base…'}</span>}
  </>;
}
