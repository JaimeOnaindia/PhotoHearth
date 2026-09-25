import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Globe2, MapPin, ShieldCheck } from 'lucide-react';
import { api, dateLabel, errorMessage, fileUrl, type Photo, type PhotoPage, type Place, type PlacePage } from './api';
import { MapCanvas } from './MapCanvas';
import './styles/places.css';

export function Places({ revision, onOpen }: { revision: number; onOpen: (photo: Photo) => void }) {
  const [data, setData] = useState<PlacePage | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [enabled, setEnabled] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectPlace = useCallback((id: string) => setSelectedId(id), []);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<PlacePage>('/places', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setData(result);
    }).catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); });
    return () => controller.abort();
  }, [revision, retry]);
  const selected = data?.items.find(place => place.id === selectedId);
  if (error) return <div className="connection-error" role="alert"><h2>No podemos cargar tus lugares</h2><p>{error}</p><button className="button" onClick={() => setRetry(value => value + 1)}>Reintentar mapa</button></div>;
  if (!data) return <p role="status">Buscando los lugares de tus recuerdos…</p>;
  return <section className="places-page">
    <div className="places-intro"><div><span className="eyebrow">VUESTRO PEQUEÑO ATLAS</span><h2>Hay lugares que se quedan contigo.</h2><p>Cada punto, una historia. Cada foto, una forma de volver.</p></div><div className="places-totals"><strong>{data.total}<small>zonas visitadas</small></strong><strong>{data.located}<small>fotos con ubicación</small></strong></div></div>
    <div className="places-map-frame">
      <MapCanvas places={data.items} selected={selectedId} enabled={enabled} onSelect={selectPlace} />
      {!enabled && <div className="map-consent"><Globe2 size={46} strokeWidth={1.2} /><h3>El mundo, un recuerdo a la vez.</h3><p>El mapa base se descarga de OpenStreetMap. Ese servicio podrá conocer tu IP y la zona que consultas, pero no recibe tus fotos.</p><button className="button primary" onClick={() => setEnabled(true)}>Activar mapa</button><small>Puedes explorar la lista de lugares sin activarlo.</small></div>}
      {enabled && <span className="map-private-badge"><ShieldCheck size={14} /> Tus fotos se quedan en casa</span>}
    </div>
    <div className="map-footnote"><span><MapPin size={14} /> Agrupamos fotos cercanas; no representan necesariamente ciudades distintas.</span>{enabled && <button className="button subtle" onClick={() => setEnabled(false)}>Desactivar mapa externo</button>}</div>
    {data.missing > 0 && <p className="places-missing">{data.missing} fotos no tienen ubicación. Abre una foto y pulsa «Ubicación» para añadirla. Si tu cámara guarda GPS, lo leeremos al subirla.</p>}
    {selected ? <PlacePhotos key={`${selected.id}:${revision}`} place={selected} onBack={() => setSelectedId(null)} onOpen={onOpen} /> : <>
      <div className="places-list-heading"><h2>Donde hemos estado</h2><span>{data.total} zonas</span></div>
      {!data.items.length && <div className="places-empty"><MapPin size={30} /><h3>El primer punto está por llegar.</h3><p>Sube fotos con GPS o añade una ubicación a tus fotos para empezar vuestro mapa.</p></div>}
      <div className="places-grid">{data.items.map((place, index) => <button className="place-card" key={place.id} onClick={() => selectPlace(place.id)}>
        <div className="place-cover"><img src={fileUrl(place.cover, 'preview')} alt="" loading="lazy" /><span>{place.count} {place.count === 1 ? 'recuerdo' : 'recuerdos'}</span></div>
        <div className="place-caption"><span className="eyebrow">LUGAR {String(index + 1).padStart(2, '0')}</span><h3>{place.name || `${place.latitude.toFixed(3)}°, ${place.longitude.toFixed(3)}°`}</h3><p>{dateLabel(place.last_visit)}</p></div>
      </button>)}</div>
      {data.total > data.items.length && <p>Mostrando las {data.items.length} zonas visitadas más recientemente de {data.total}.</p>}
    </>}
  </section>;
}

function PlacePhotos({ place, onBack, onOpen }: { place: Place; onBack: () => void; onOpen: (photo: Photo) => void }) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [offset, setOffset] = useState(0);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError('');
    api<PhotoPage>(`/photos?place=${encodeURIComponent(place.id)}&offset=${offset}`, { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) {
        setPhotos(previous => offset === 0 ? result.items : [...previous, ...result.items]); setTotal(result.total);
      }
    }).catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [place.id, offset, retry]);
  return <section className="place-photos"><button className="button subtle" onClick={onBack}><ArrowLeft size={16} /> Todos los lugares</button><h2>{place.name || 'Recuerdos de este lugar'}</h2>
    {error && <div role="alert"><p>{error}</p><button className="button" onClick={() => setRetry(value => value + 1)}>Reintentar fotos</button></div>}
    <div className="photo-grid">{photos.map(photo => <button key={photo.id} className="photo-card photo-open" aria-label={`Abrir ${photo.filename}`} onClick={() => onOpen(photo)}><img src={fileUrl(photo.id)} alt={photo.filename} loading="lazy" /></button>)}</div>
    {busy ? <p role="status">Cargando recuerdos…</p> : !error && photos.length < total && <button className="button" onClick={() => setOffset(photos.length)}>Ver más recuerdos del lugar</button>}
  </section>;
}
