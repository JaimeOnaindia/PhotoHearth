import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, Heart, ImageOff, RotateCcw, Trash2 } from 'lucide-react';
import { bytes, dateLabel, fileUrl, type Photo } from './api';
import { Modal } from './ui';

export function Lightbox({ photo, previous, next, onClose, onUpdate, onAlbum, onRemove, busy }: {
  photo: Photo; previous?: () => void; next?: () => void; onClose: () => void;
  onUpdate: (patch: { favorite?: boolean; trashed?: boolean }) => void;
  onAlbum: () => void; onRemove?: () => void; busy: boolean;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft') previous?.();
      if (e.key === 'ArrowRight') next?.();
    };
    window.addEventListener('keydown', key);
    return () => window.removeEventListener('keydown', key);
  }, [previous, next]);
  return <Modal title={photo.filename} onClose={onClose} className="lightbox">
    <div className="viewer-image">{failed ? <div className="preview-error"><ImageOff /><p>No se ha podido cargar la imagen.</p><button className="button" onClick={() => setFailed(false)}>Reintentar</button></div> :
      <img src={fileUrl(photo.id, 'preview')} alt={photo.filename} onError={() => setFailed(true)} />}
      <button className="viewer-arrow prev" aria-label="Foto anterior" disabled={!previous} onClick={previous}><ChevronLeft /></button>
      <button className="viewer-arrow next" aria-label="Foto siguiente" disabled={!next} onClick={next}><ChevronRight /></button>
    </div><div className="viewer-info"><div><span className="eyebrow">UN MOMENTO TUYO</span><h2>{photo.filename}</h2><p>{dateLabel(photo.taken_at)} · {photo.width} × {photo.height} · {bytes(photo.bytes)}</p></div>
      <div className="viewer-actions"><a className="icon-button" href={fileUrl(photo.id, 'original')} download aria-label="Descargar original"><Download size={20} /></a>
        <button className={`icon-button ${photo.favorite ? 'is-favorite' : ''}`} disabled={busy} aria-label={photo.favorite ? 'Quitar de favoritos' : 'Añadir a favoritos'} aria-pressed={photo.favorite} onClick={() => onUpdate({ favorite: !photo.favorite })}><Heart size={20} fill={photo.favorite ? 'currentColor' : 'none'} /></button>
        <button className="icon-button" disabled={busy} aria-label={photo.deleted_at ? 'Restaurar foto' : 'Mover a la papelera'} onClick={() => onUpdate({ trashed: !photo.deleted_at })}>{photo.deleted_at ? <RotateCcw size={20} /> : <Trash2 size={20} />}</button>
        {!photo.deleted_at && <button className="button" disabled={busy} onClick={onAlbum}>Añadir a álbum</button>}
        {onRemove && <button className="button subtle" disabled={busy} onClick={onRemove}>Quitar del álbum</button>}
      </div></div>
  </Modal>;
}
