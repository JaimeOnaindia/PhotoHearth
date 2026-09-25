import { Check, Heart } from 'lucide-react';
import { dateLabel, fileUrl, type Photo } from './api';

export function Gallery({ photos, selected, onSelect, onOpen, compact }: {
  photos: Photo[]; selected: Set<string>; onSelect: (id: string) => void;
  onOpen: (photo: Photo) => void; compact: boolean;
}) {
  const days = new Map<string, Photo[]>();
  photos.forEach(photo => { const day = photo.taken_at.slice(0, 10); days.set(day, [...(days.get(day) ?? []), photo]); });
  return <div className={`timeline ${compact ? 'compact' : ''}`}>{[...days].map(([day, photos]) =>
    <section className="day-group" key={day}><div className="day-heading"><h2>{dateLabel(`${day}T12:00:00`)}</h2><span>{photos.length} {photos.length === 1 ? 'foto' : 'fotos'}</span></div>
      <div className="photo-grid">{photos.map(photo => <article className={`photo-card ${selected.has(photo.id) ? 'selected' : ''}`} key={photo.id}>
        <button className="photo-open" aria-label={`Abrir ${photo.filename}`} onClick={() => onOpen(photo)}>
          <img src={fileUrl(photo.id)} alt={photo.filename} loading="lazy" decoding="async" width={photo.width} height={photo.height} />
          <span className="photo-caption">{photo.filename}</span>
        </button><button className="select-photo" aria-label={`Seleccionar ${photo.filename}`} aria-pressed={selected.has(photo.id)} onClick={() => onSelect(photo.id)}><Check size={15} /></button>
        {photo.favorite && <span className="photo-heart" aria-label="Favorita"><Heart size={16} fill="currentColor" /></span>}
      </article>)}</div>
    </section>)}</div>;
}
