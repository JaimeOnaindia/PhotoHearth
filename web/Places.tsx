import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Check, Globe2, Images, LocateFixed, MapPin, MousePointer2, ShieldCheck } from 'lucide-react';
import { api, dateLabel, errorMessage, fileUrl, type Photo, type PhotoPage, type Place, type PlacePage } from './api';
import { MapCanvas, type MapPoint } from './MapCanvas';
import './styles/places.css';

export function Places({ revision, csrf, onOpen }: {
  revision: number; csrf: string; onOpen: (photo: Photo) => void;
}) {
  const [data, setData] = useState<PlacePage | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [enabled, setEnabled] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [organizing, setOrganizing] = useState(false);
  const [missingPhotos, setMissingPhotos] = useState<Photo[]>([]);
  const [missingTotal, setMissingTotal] = useState(0);
  const [missingBusy, setMissingBusy] = useState(false);
  const [missingError, setMissingError] = useState('');
  const [selectedMissing, setSelectedMissing] = useState<Set<string>>(new Set());
  const [draft, setDraft] = useState<MapPoint | null>(null);
  const [placeName, setPlaceName] = useState('');
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState('');
  const selectPlace = useCallback((id: string) => setSelectedId(id), []);
  const pickLocation = useCallback((latitude: number, longitude: number) => {
    setDraft({ latitude, longitude });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api<PlacePage>('/places', { signal: controller.signal }).then(result => {
      if (!controller.signal.aborted) setData(result);
    }).catch(error => { if (!controller.signal.aborted) setError(errorMessage(error)); });
    return () => controller.abort();
  }, [revision, retry]);

  useEffect(() => {
    if (!organizing) return;
    const controller = new AbortController();
    setMissingBusy(true); setMissingError('');
    api<PhotoPage>('/photos?location=missing&limit=120', { signal: controller.signal }).then(result => {
      if (controller.signal.aborted) return;
      setMissingPhotos(result.items); setMissingTotal(result.total);
      const visible = new Set(result.items.map(photo => photo.id));
      setSelectedMissing(previous => new Set([...previous].filter(id => visible.has(id))));
    }).catch(error => { if (!controller.signal.aborted) setMissingError(errorMessage(error)); })
      .finally(() => { if (!controller.signal.aborted) setMissingBusy(false); });
    return () => controller.abort();
  }, [organizing, revision, retry]);

  const selected = data?.items.find(place => place.id === selectedId);
  const photoTotal = data ? data.located + data.missing : 0;
  const coverage = photoTotal ? Math.round((data!.located / photoTotal) * 100) : 0;

  function toggleOrganizer() {
    setOrganizing(value => !value); setSelectedId(null); setNotice('');
    setSelectedMissing(new Set()); setDraft(null); setPlaceName('');
  }

  function toggleMissing(id: string) {
    setSelectedMissing(previous => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAllMissing() {
    setSelectedMissing(previous => previous.size === missingPhotos.length
      ? new Set()
      : new Set(missingPhotos.map(photo => photo.id)));
  }

  async function assignLocation() {
    if (!draft || !selectedMissing.size) return;
    setSaving(true); setMissingError('');
    try {
      const result = await api<{ updated: number }>('/photos/batch', {
        method: 'PATCH',
        body: JSON.stringify({
          ids: [...selectedMissing],
          location: { ...draft, name: placeName },
        }),
      }, csrf);
      const destination = placeName.trim() ? ` en ${placeName.trim()}` : '';
      setNotice(`${result.updated} ${result.updated === 1 ? 'foto situada' : 'fotos situadas'}${destination}.`);
      setSelectedMissing(new Set()); setDraft(null); setPlaceName(''); setOrganizing(false);
      setRetry(value => value + 1);
    } catch (error) { setMissingError(errorMessage(error)); }
    finally { setSaving(false); }
  }

  if (error) return <div className="connection-error" role="alert"><h2>No podemos cargar tus lugares</h2><p>{error}</p><button className="button" onClick={() => setRetry(value => value + 1)}>Reintentar mapa</button></div>;
  if (!data) return <p role="status">Buscando los lugares de tus recuerdos…</p>;
  return <section className="places-page">
    <div className="places-intro"><div><span className="eyebrow">VUESTRO PEQUEÑO ATLAS</span><h2>Hay lugares que se quedan contigo.</h2><p>Cada punto, una historia. Cada foto, una forma de volver.</p></div><div className="places-totals">
      <strong>{data.total}<small>zonas visitadas</small></strong>
      <strong>{data.located}<small>fotos situadas</small></strong>
      <div className="coverage-ring" role="progressbar" aria-label="Fotos con ubicación" aria-valuemin={0} aria-valuemax={100} aria-valuenow={coverage} style={{ background: `conic-gradient(var(--green) ${coverage * 3.6}deg, #dfe5d9 0deg)` }}><span>{coverage}%<small>del atlas</small></span></div>
    </div></div>
    {notice && <p className="places-notice" role="status"><Check size={16} /> {notice}</p>}
    {data.missing > 0 && <div className={`places-missing ${organizing ? 'active' : ''}`}><span className="missing-icon"><Images size={23} /></span><div><strong>{data.missing} {data.missing === 1 ? 'foto necesita' : 'fotos necesitan'} un lugar</strong><p>Algunas aplicaciones eliminan el GPS al compartir. Puedes situarlas juntas sin modificar los originales.</p></div><button className="button primary" onClick={toggleOrganizer}>{organizing ? 'Cerrar organizador' : 'Organizar fotos sin ubicación'}</button></div>}
    {organizing && <section className="location-workbench" aria-label="Fotos sin ubicación"><div className="workbench-heading"><span>1</span><div><strong>Elige los recuerdos del mismo lugar</strong><p>Puedes organizar hasta 120 fotos cada vez.</p></div><button className="button subtle" disabled={!missingPhotos.length} onClick={toggleAllMissing}>{selectedMissing.size === missingPhotos.length && missingPhotos.length ? 'Quitar selección' : 'Seleccionar todas'}</button></div>
      {missingError && <div className="workbench-error" role="alert"><p>{missingError}</p><button className="button" onClick={() => setRetry(value => value + 1)}>Reintentar</button></div>}
      {missingBusy ? <p role="status">Buscando fotos sin ubicación…</p> : <div className="missing-photo-strip">{missingPhotos.map(photo => <button key={photo.id} className="missing-photo" aria-label={`Seleccionar ${photo.filename}`} aria-pressed={selectedMissing.has(photo.id)} onClick={() => toggleMissing(photo.id)}><img src={fileUrl(photo.id)} alt="" loading="lazy" /><span className="missing-photo-check"><Check size={14} /></span><small>{photo.filename}</small></button>)}</div>}
      {missingTotal > missingPhotos.length && <p className="workbench-limit">Mostrando las primeras {missingPhotos.length} de {missingTotal}. Guarda este grupo para continuar con las siguientes.</p>}
    </section>}
    <div className={`places-map-frame ${organizing ? 'organizing' : ''}`}>
      <MapCanvas places={data.items} selected={selectedId} enabled={enabled} onSelect={selectPlace} draft={draft} picking={organizing && enabled} onPick={organizing && enabled ? pickLocation : undefined} />
      {!enabled && <div className="map-consent"><Globe2 size={46} strokeWidth={1.2} /><h3>El mundo, un recuerdo a la vez.</h3><p>El mapa base se descarga de OpenStreetMap. Ese servicio podrá conocer tu IP y la zona que consultas, pero no recibe tus fotos.</p><button className="button primary" onClick={() => setEnabled(true)}>{organizing ? 'Activar mapa para elegir el lugar' : 'Activar mapa'}</button><small>Puedes explorar la lista de lugares sin activarlo.</small></div>}
      {enabled && <span className="map-private-badge"><ShieldCheck size={14} /> Tus fotos se quedan en casa</span>}
      {organizing && enabled && <span className="map-pick-hint"><MousePointer2 size={15} /> Pulsa el punto exacto en el mapa</span>}
    </div>
    <div className="map-footnote"><span><MapPin size={14} /> Agrupamos fotos cercanas. Los nombres aproximados proceden de <a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a> y se buscan en casa.</span>{enabled && <button className="button subtle" onClick={() => setEnabled(false)}>Desactivar mapa externo</button>}</div>
    {organizing && <div className="location-assignment"><span className="assignment-step">2</span><div className="assignment-copy"><strong>Nombra el lugar y guarda el grupo</strong><p>{draft ? `${draft.latitude.toFixed(5)}°, ${draft.longitude.toFixed(5)}°` : 'Todavía no has marcado ningún punto.'}</p></div><label>Nombre del lugar<input value={placeName} maxLength={120} placeholder="Por ejemplo, Bilbao" onChange={event => setPlaceName(event.target.value)} /></label><button className="button primary" disabled={saving || !draft || !selectedMissing.size} onClick={() => void assignLocation()}><LocateFixed size={17} /> {saving ? 'Guardando…' : `Situar ${selectedMissing.size || ''} ${selectedMissing.size === 1 ? 'foto' : 'fotos'}`}</button></div>}
    {selected ? <PlacePhotos key={`${selected.id}:${revision}`} place={selected} onBack={() => setSelectedId(null)} onOpen={onOpen} /> : <>
      <div className="places-list-heading"><h2>Donde hemos estado</h2><span>{data.total} zonas</span></div>
      {!data.items.length && <div className="places-empty"><MapPin size={30} /><h3>El primer punto está por llegar.</h3><p>Sube originales con GPS o usa el organizador para empezar vuestro mapa.</p></div>}
      <div className="places-grid">{data.items.map(place => <button className="place-card" key={place.id} onClick={() => selectPlace(place.id)}>
        <div className="place-cover"><img src={fileUrl(place.cover, 'preview')} alt="" loading="lazy" /><span>{place.count} {place.count === 1 ? 'recuerdo' : 'recuerdos'}</span></div>
        <div className="place-caption"><span className="eyebrow">{place.name ? 'NOMBRE ASIGNADO' : place.nearby_name ? 'LOCALIDAD CERCANA' : 'SIN NOMBRE'}</span><h3>{place.name || place.nearby_name || `${place.latitude.toFixed(3)}°, ${place.longitude.toFixed(3)}°`}</h3><p>{dateLabel(place.last_visit)}</p></div>
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
  return <section className="place-photos"><button className="button subtle" onClick={onBack}><ArrowLeft size={16} /> Todos los lugares</button><h2>{place.name || place.nearby_name || 'Recuerdos de este lugar'}</h2>
    {error && <div role="alert"><p>{error}</p><button className="button" onClick={() => setRetry(value => value + 1)}>Reintentar fotos</button></div>}
    <div className="photo-grid">{photos.map(photo => <button key={photo.id} className="photo-card photo-open" aria-label={`Abrir ${photo.filename}`} onClick={() => onOpen(photo)}><img src={fileUrl(photo.id)} alt={photo.filename} loading="lazy" /></button>)}</div>
    {busy ? <p role="status">Cargando recuerdos…</p> : !error && photos.length < total && <button className="button" onClick={() => setOffset(photos.length)}>Ver más recuerdos del lugar</button>}
  </section>;
}
