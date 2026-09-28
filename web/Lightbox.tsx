import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Download, Heart, ImageOff, RotateCcw, Trash2 } from 'lucide-react';
import { bytes, dateLabel, fileUrl, type Photo, type PhotoPatch } from './api';
import { LocationEditor } from './LocationEditor';
import { Modal } from './ui';

export function Lightbox({ photo, previous, next, onClose, onUpdate, onAlbum, onRemove, onCover, onCoverReset, coverPosition, busy, notice }: {
  photo: Photo; previous?: () => void; next?: () => void; onClose: () => void;
  onUpdate: (patch: PhotoPatch) => Promise<boolean>;
  onAlbum: () => void; onRemove?: () => void; busy: boolean; notice: string;
  onCover?: (x: number, y: number) => Promise<boolean>;
  onCoverReset?: () => Promise<boolean>;
  coverPosition?: { x: number; y: number };
}) {
  const [failed, setFailed] = useState(false);
  const [editingCover, setEditingCover] = useState(false);
  const [coverX, setCoverX] = useState(coverPosition?.x ?? 50);
  const [coverY, setCoverY] = useState(coverPosition?.y ?? 50);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
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
        {onCover && <button className="button" disabled={busy} onClick={() => setEditingCover(value => !value)}>{coverPosition ? 'Ajustar portada' : 'Usar como portada'}</button>}
        {onRemove && <button className="button subtle" disabled={busy} onClick={onRemove}>Quitar del álbum</button>}
      </div></div>
    {editingCover && onCover && <section className="cover-editor" aria-label="Ajustar portada"><div className="cover-editor-preview"><img src={fileUrl(photo.id, 'preview')} alt="Vista previa de portada" style={{ objectPosition: `${coverX}% ${coverY}%` }} /></div><div className="cover-editor-controls"><h3>Encuadra la portada</h3><label>Horizontal<input aria-label="Posición horizontal de la portada" type="range" min="0" max="100" value={coverX} onChange={event => setCoverX(Number(event.target.value))} /></label><label>Vertical<input aria-label="Posición vertical de la portada" type="range" min="0" max="100" value={coverY} onChange={event => setCoverY(Number(event.target.value))} /></label><div><button className="button primary" disabled={busy} onClick={() => void onCover(coverX, coverY).then(saved => { if (saved) setEditingCover(false); })}>Guardar portada</button>{onCoverReset && <button className="button subtle" disabled={busy} onClick={() => void onCoverReset().then(saved => { if (saved) setEditingCover(false); })}>Volver a portada automática</button>}</div></div></section>}
    {notice && <p className="notice" role="status">{notice}</p>}
    <LocationEditor photo={photo} busy={busy} onUpdate={onUpdate} />
  </Modal>;
}
