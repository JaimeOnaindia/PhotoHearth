import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowUpRight, Check, FolderHeart, Grid2X2, HardDrive, Heart, Images, LayoutGrid, LogOut, MapPin, Plus, RotateCcw, Search, Settings2, ShieldCheck, Trash2, Upload, X } from 'lucide-react';
import { api, bytes, errorMessage, type Photo, type PhotoPatch, type User, type View } from './api';
import { Albums, AlbumModal } from './Albums';
import { Gallery } from './Gallery';
import { Lightbox } from './Lightbox';
import { Settings } from './Settings';
import { UploadPanel } from './UploadPanel';
import { Brand, EmptyState } from './ui';
import { useLibrary } from './useLibrary';
import { useUpload } from './useUpload';

const Places = lazy(() => import('./Places').then(module => ({ default: module.Places })));

const nav = [
  { id: 'library', label: 'Todas las fotos', icon: Images },
  { id: 'favorites', label: 'Favoritos', icon: Heart },
  { id: 'albums', label: 'Álbumes', icon: FolderHeart },
  { id: 'places', label: 'Lugares', icon: MapPin },
  { id: 'trash', label: 'Papelera', icon: Trash2 },
  { id: 'settings', label: 'Mi hogar', icon: Settings2 },
] as const;
const titles: Record<View, string> = { library: 'Tu vida, en imágenes.', favorites: 'Las que más te importan.', albums: 'Historias que van juntas.', trash: 'Por si cambias de idea.', settings: 'Aquí viven tus recuerdos.', places: 'Nuestro mundo, en recuerdos.' };

export function App({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [view, setView] = useState<View>('library');
  const [albumId, setAlbumId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [focused, setFocused] = useState<Photo | null>(null);
  const [albumPhotos, setAlbumPhotos] = useState<string[] | null>(null);
  const [compact, setCompact] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const refresh = useCallback(() => setRevision(v => v + 1), []);
  const library = useLibrary(view, search, albumId, revision);
  const upload = useUpload(user.csrf, refresh);
  const album = library.albums.find(a => a.id === albumId);
  const photoView = !['settings', 'albums', 'places'].includes(view) || albumId !== null;
  const focusIndex = view === 'places' ? -1 : library.items.findIndex(p => p.id === focused?.id);

  useEffect(() => { const timer = setTimeout(() => setSearch(query), 250); return () => clearTimeout(timer); }, [query]);
  function navigate(next: View, id: string | null = null) {
    setView(next); setAlbumId(id); setQuery(''); setSearch(''); setSelected(new Set()); setNotice('');
  }
  function toggle(id: string) { setSelected(previous => { const result = new Set(previous); if (result.has(id)) result.delete(id); else result.add(id); return result; }); }
  function pickFiles() { fileInput.current?.click(); }
  async function change(ids: string[], patch: PhotoPatch): Promise<boolean> {
    setActionBusy(true); setNotice('');
    try {
      for (const id of ids) {
        const updated = await api<Photo>(`/photos/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }, user.csrf);
        if (focused?.id === id) setFocused(patch.trashed !== undefined ? null : updated);
      }
      setSelected(new Set());
      setNotice('location' in patch ? 'Ubicación actualizada.' : patch.trashed === true ? 'Fotos movidas a la papelera. Puedes restaurarlas cuando quieras.' : patch.trashed === false ? 'Fotos de vuelta en tu biblioteca.' : 'Favoritos actualizados.');
      return true;
    } catch (error) { setNotice(errorMessage(error)); return false; }
    finally { setActionBusy(false); refresh(); }
  }
  async function removeFromAlbum() {
    if (!focused || !albumId) return;
    setActionBusy(true);
    try { await api(`/albums/${albumId}/photos/${focused.id}`, { method: 'DELETE' }, user.csrf); setFocused(null); refresh(); }
    catch (error) { setNotice(errorMessage(error)); }
    finally { setActionBusy(false); }
  }
  async function logout() {
    setActionBusy(true);
    try { await api('/auth/logout', { method: 'POST' }, user.csrf); onLogout(); }
    catch (error) { setNotice(errorMessage(error)); }
    finally { setActionBusy(false); }
  }
  const counts: Partial<Record<View, number>> = library.stats ? { library: library.stats.photos, favorites: library.stats.favorites, albums: library.stats.albums, trash: library.stats.trash } : {};
  return <div className="app-shell"><a className="skip-link" href="#main">Ir a la biblioteca</a>
    <aside className="sidebar"><Brand /><div className="sidebar-section-label">TU BIBLIOTECA</div><nav aria-label="Navegación principal">
      {nav.map(({ id, label, icon: Icon }) => <button key={id} className={`nav-item ${view === id ? 'active' : ''}`} onClick={() => navigate(id)} aria-current={view === id ? 'page' : undefined}><Icon size={20} strokeWidth={1.6} /><span>{label}</span>{counts[id] !== undefined && <small>{counts[id]}</small>}</button>)}
    </nav><div className="sidebar-lower"><div className="home-card"><div><span className="home-icon"><HardDrive size={19} /></span><span>Tu servidor<small><span className={`status-dot ${library.error ? 'offline' : ''}`} />{library.error ? 'Sin conexión' : library.stats ? 'Conectado a casa' : 'Conectando…'}</small></span></div>
      {library.stats && <><progress aria-label="Uso del disco" value={library.stats.disk_total - library.stats.disk_free} max={library.stats.disk_total} /><p>{bytes(library.stats.disk_free)} disponibles</p></>}
      <button onClick={() => navigate('settings')}>Ver mi almacenamiento <ArrowUpRight size={14} /></button></div>
      <div className="sidebar-privacy"><ShieldCheck size={15} /> Tus fotos te pertenecen.</div>
    </div></aside>
    <div className="workspace"><header className="topbar"><div className="mobile-brand"><Brand compact /></div>
      <div className="breadcrumb">Mi espacio <span>/</span> <strong>{nav.find(n => n.id === view)?.label}</strong></div>
      <div className="topbar-right"><span className="local-label"><span className="status-dot" /> Alojado en casa</span><span className="avatar" title={user.name}>{user.name.slice(0, 1).toUpperCase()}</span><button className="icon-button logout" disabled={actionBusy} onClick={() => void logout()} aria-label="Cerrar sesión"><LogOut size={18} /></button></div>
    </header><main id="main" className={`main-content ${dragging ? 'dragging' : ''}`} onDragOver={e => { if (e.dataTransfer.types.includes('Files')) { e.preventDefault(); setDragging(true); } }} onDragLeave={e => { if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false); }} onDrop={e => { e.preventDefault(); setDragging(false); void upload.upload(Array.from(e.dataTransfer.files)); }}>
      {dragging && <div className="drop-overlay"><Upload size={48} /><h2>Un nuevo recuerdo llega a casa.</h2><p>Suelta tus fotos aquí</p></div>}
      <input ref={fileInput} type="file" multiple accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" className="visually-hidden" aria-label="Seleccionar fotos para subir" onChange={e => { void upload.upload(Array.from(e.target.files ?? [])); e.target.value = ''; }} />
      <div className="page-heading"><div><span className="eyebrow">{album ? 'TU COLECCIÓN' : view === 'library' ? 'CADA DÍA MERECE UN RECUERDO' : 'HECHO DE TUS MOMENTOS'}</span>
        {album && <button className="back-button" onClick={() => navigate('albums')}><ArrowLeft size={15} /> Todos los álbumes</button>}
        <h1>{album?.name ?? titles[view]}</h1><p>{view === 'trash' ? 'Las fotos se conservan aquí hasta que decidas restaurarlas. No se borran automáticamente.' : view === 'settings' ? 'Tu espacio privado, bajo tu control.' : view === 'albums' && !album ? 'Un viaje, una persona, una época. Dales su propio lugar.' : 'Todos esos pequeños momentos, en un lugar solo tuyo.'}</p></div>
        <div className="heading-actions">{view === 'albums' && !album ? <button className="button primary" onClick={() => setAlbumPhotos([])}><Plus size={18} /> Nuevo álbum</button> : view !== 'settings' && view !== 'trash' && <button className="button primary" disabled={!!upload.state && !upload.state.done} onClick={pickFiles}><Plus size={19} /> Añadir fotos</button>}</div>
      </div>
      {view === 'library' && !search && !album && <div className="welcome-strip"><span className="welcome-flower">✳</span><div><strong>Un hogar para lo que no quieres olvidar.</strong><p>Sin comprimir tus recuerdos. Sin compartir tus datos.</p></div><span className="strip-tag"><ShieldCheck size={14} /> 100% tuyo</span></div>}
      {photoView && <div className="library-toolbar"><div className="library-tabs"><span className="active">{view === 'favorites' ? 'Favoritos' : view === 'trash' ? 'Papelera' : 'Fotografías'}</span><small>{library.total.toLocaleString('es')}</small></div>
        <div className="toolbar-controls"><div className="search-field"><Search size={17} /><input aria-label="Buscar fotos" placeholder="Buscar por nombre o fecha…" value={query} maxLength={200} onChange={e => { setQuery(e.target.value); setSelected(new Set()); }} />{query && <button className="icon-button" onClick={() => setQuery('')} aria-label="Limpiar búsqueda"><X size={15} /></button>}</div>
        <div className="density-switch"><button aria-label="Vista amplia" aria-pressed={!compact} className={!compact ? 'active' : ''} onClick={() => setCompact(false)}><Grid2X2 size={17} /></button><button aria-label="Vista compacta" aria-pressed={compact} className={compact ? 'active' : ''} onClick={() => setCompact(true)}><LayoutGrid size={17} /></button></div></div>
      </div>}
      {notice && <div className="notice" role="status"><span>{notice}</span><button className="icon-button" aria-label="Cerrar aviso" onClick={() => setNotice('')}><X size={16} /></button></div>}
      {selected.size > 0 && <div className="selection-bar"><button className="icon-button" aria-label="Cancelar selección" onClick={() => setSelected(new Set())}><X size={18} /></button><strong>{selected.size} seleccionadas</strong>
        {view !== 'trash' && <><button className="button" disabled={actionBusy} onClick={() => setAlbumPhotos([...selected])}><FolderHeart size={17} /> Añadir a álbum</button><button className="icon-button" disabled={actionBusy} aria-label="Marcar selección como favorita" onClick={() => void change([...selected], { favorite: true })}><Heart size={18} /></button></>}
        <button className="button" disabled={actionBusy} onClick={() => void change([...selected], { trashed: view !== 'trash' })}>{view === 'trash' ? <RotateCcw size={17} /> : <Trash2 size={17} />}{view === 'trash' ? 'Restaurar' : 'A la papelera'}</button>
      </div>}
      {view === 'places' ? <Suspense fallback={<p>Cargando el mapa…</p>}><Places revision={revision} onOpen={photo => { setFocused(photo); setNotice(''); }} /></Suspense> : library.error ? <div className="connection-error" role="alert"><HardDrive size={30} /><h2>No podemos abrir tu biblioteca</h2><p>{library.error}</p><button className="button" onClick={refresh}>Volver a intentar</button></div> : library.busy ? <div className="skeleton-grid" aria-label="Cargando biblioteca" aria-busy="true">{Array.from({ length: 8 }, (_, i) => <div key={i} />)}</div> : view === 'settings' ? <Settings stats={library.stats} name={user.name} csrf={user.csrf} onPasswordChanged={onLogout} /> : view === 'albums' && !albumId ? <Albums albums={library.albums} onOpen={id => navigate('albums', id)} onCreate={() => setAlbumPhotos([])} /> : library.items.length === 0 ?
        <EmptyState title={search ? 'No encontramos esos recuerdos.' : view === 'favorites' ? 'Un lugar para tus imprescindibles.' : view === 'trash' ? 'Todo está en su sitio.' : albumId ? 'Esta historia está por empezar.' : 'Tu historia empieza aquí.'} text={search ? 'Prueba otro nombre de archivo o una fecha como 2026-09.' : view === 'favorites' ? 'Toca el corazón de una foto y la encontrarás aquí.' : view === 'trash' ? 'Las fotos que muevas a la papelera aparecerán aquí.' : albumId ? 'Selecciona fotos en tu biblioteca y añádelas a este álbum.' : 'Añade tus primeras fotos y construye un hogar para tus recuerdos. Puedes arrastrarlas aquí o elegirlas desde tu dispositivo.'} action={view === 'library' && !search ? pickFiles : undefined} /> :
        <><Gallery photos={library.items} selected={selected} onSelect={toggle} onOpen={photo => { setFocused(photo); setNotice(''); }} compact={compact} />{library.items.length < library.total && <div className="load-more"><button className="button" disabled={library.moreBusy} onClick={() => void library.loadMore()}>{library.moreBusy ? 'Cargando…' : 'Ver más recuerdos'}</button><small>{library.items.length} de {library.total} fotos</small></div>}</>}
      <footer className="library-footer"><span><Check size={13} /> Originales conservados</span><span>Un poquito de vida, bien guardada.</span></footer>
    </main></div>
    {focused && <Lightbox key={focused.id} photo={focused} busy={actionBusy} notice={notice} previous={focusIndex > 0 ? () => setFocused(library.items[focusIndex - 1]) : undefined} next={focusIndex >= 0 && focusIndex < library.items.length - 1 ? () => setFocused(library.items[focusIndex + 1]) : undefined} onClose={() => setFocused(null)} onUpdate={patch => change([focused.id], patch)} onAlbum={() => { setAlbumPhotos([focused.id]); setFocused(null); }} onRemove={albumId ? () => void removeFromAlbum() : undefined} />}
    {albumPhotos !== null && <AlbumModal albums={library.albums} photoIds={albumPhotos} csrf={user.csrf} onClose={() => { setAlbumPhotos(null); refresh(); }} onDone={id => { setAlbumPhotos(null); setSelected(new Set()); navigate('albums', id); refresh(); }} />}
    {upload.state && <UploadPanel state={upload.state} onCancel={upload.cancel} onDismiss={upload.dismiss} onRetry={files => void upload.upload(files)} />}
  </div>;
}
