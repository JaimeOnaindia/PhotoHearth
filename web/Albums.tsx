import { useState, type FormEvent } from 'react';
import { FolderHeart, Plus } from 'lucide-react';
import { api, errorMessage, fileUrl, type Album } from './api';
import { Modal } from './ui';

export function Albums({ albums, onOpen, onCreate }: { albums: Album[]; onOpen: (id: string) => void; onCreate: () => void }) {
  return <div className="album-grid">{albums.map(album => <button className="album-card" key={album.id} onClick={() => onOpen(album.id)}>
    <div className="album-cover">{album.cover ? <img src={fileUrl(album.cover, 'preview')} alt="" loading="lazy" /> : <FolderHeart size={46} strokeWidth={1} />}</div>
    <h2>{album.name}</h2><p>{album.count} {album.count === 1 ? 'foto' : 'fotos'}</p>
  </button>)}<button className="new-album" onClick={onCreate}><span><Plus size={28} /></span><h2>Una nueva historia</h2><p>Crear un álbum</p></button></div>;
}

export function AlbumModal({ albums, photoIds, csrf, onClose, onDone }: {
  albums: Album[]; photoIds: string[]; csrf: string; onClose: () => void; onDone: (id: string) => void;
}) {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function save(id?: string) {
    setBusy(true); setError('');
    try {
      const albumId = id ?? (await api<Album>('/albums', { method: 'POST', body: JSON.stringify({ name: name.trim() }) }, csrf)).id;
      for (const photo of photoIds) await api(`/albums/${albumId}/photos/${photo}`, { method: 'PUT' }, csrf);
      onDone(albumId);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <Modal title={photoIds.length ? 'Añadir a un álbum' : 'Crear un álbum'} onClose={() => { if (!busy) onClose(); }}>
    <span className="modal-emblem"><FolderHeart size={27} /></span><h2>{photoIds.length ? 'Cada momento, en su lugar.' : 'Empieza una nueva historia.'}</h2>
    <p>{photoIds.length ? `${photoIds.length} fotos seleccionadas. Elige un álbum o crea uno nuevo.` : 'Ponle un nombre a esos recuerdos que van juntos.'}</p>
    {photoIds.length > 0 && albums.length > 0 && <div className="album-choices">{albums.map(album => <button className="album-choice" key={album.id} disabled={busy} onClick={() => void save(album.id)}><FolderHeart size={18} /><span>{album.name}</span><small>{album.count} fotos</small></button>)}</div>}
    <form onSubmit={(e: FormEvent) => { e.preventDefault(); void save(); }}><label htmlFor="album-name">Nombre del nuevo álbum</label>
      <input id="album-name" value={name} onChange={e => setName(e.target.value)} placeholder="Ese verano en el norte…" required maxLength={80} />
      {error && <p className="error" role="alert">{error}</p>}<button className="button primary" disabled={busy || !name.trim()}>{busy ? 'Guardando…' : 'Crear álbum'}<Plus size={17} /></button>
    </form>
  </Modal>;
}
