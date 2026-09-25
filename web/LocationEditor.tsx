import { useState, type FormEvent } from 'react';
import { MapPin } from 'lucide-react';
import { type Photo, type PhotoPatch } from './api';

export function LocationEditor({ photo, busy, onUpdate }: {
  photo: Photo; busy: boolean; onUpdate: (patch: PhotoPatch) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState(false);
  const [latitude, setLatitude] = useState(String(photo.latitude ?? ''));
  const [longitude, setLongitude] = useState(String(photo.longitude ?? ''));
  const [name, setName] = useState(photo.location_name ?? '');
  async function save(event: FormEvent) {
    event.preventDefault();
    if (await onUpdate({ location: { latitude: Number(latitude), longitude: Number(longitude), name } })) setEditing(false);
  }
  async function clear() {
    if (await onUpdate({ location: null })) { setEditing(false); setLatitude(''); setLongitude(''); setName(''); }
  }
  return <section className="location-editor">
    <div className="location-heading"><MapPin size={18} /><div><strong>{photo.location_name || 'Ubicación'}</strong><small>{photo.latitude !== null && photo.longitude !== null ? `${photo.latitude.toFixed(5)}°, ${photo.longitude.toFixed(5)}°` : 'Esta foto todavía no tiene ubicación.'}</small></div><button className="button subtle" disabled={busy} onClick={() => setEditing(!editing)}>{editing ? 'Cancelar ubicación' : 'Editar ubicación'}</button></div>
    {editing && <form onSubmit={save}>
      <label htmlFor="location-name">Nombre del lugar</label><input id="location-name" value={name} maxLength={120} disabled={busy} placeholder="Por ejemplo, nuestro viaje a Bilbao" onChange={event => setName(event.target.value)} />
      <div className="location-coordinates"><div><label htmlFor="location-latitude">Latitud</label><input id="location-latitude" type="number" step="any" min={-90} max={90} required disabled={busy} value={latitude} onChange={event => setLatitude(event.target.value)} /></div><div><label htmlFor="location-longitude">Longitud</label><input id="location-longitude" type="number" step="any" min={-180} max={180} required disabled={busy} value={longitude} onChange={event => setLongitude(event.target.value)} /></div></div>
      <p>Coordenadas decimales. Solo cambia la ubicación del catálogo; el GPS guardado en el original no se modifica.</p>
      <div className="location-actions"><button className="button primary" disabled={busy}>Guardar ubicación</button>{photo.latitude !== null && <button className="button" type="button" disabled={busy} onClick={() => void clear()}>Quitar ubicación</button>}</div>
    </form>}
  </section>;
}
