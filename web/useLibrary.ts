import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage, type Album, type PhotoCursorPage, type PhotoPage, type Stats, type View } from './api';

export function useLibrary(view: View, query: string, album: string | null, revision: number) {
  const [page, setPage] = useState<PhotoPage>({ items: [], total: 0 });
  const [albums, setAlbums] = useState<Album[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [photoBusy, setPhotoBusy] = useState(true);
  const [metadataBusy, setMetadataBusy] = useState(true);
  const [moreBusy, setMoreBusy] = useState(false);
  const [photoError, setPhotoError] = useState('');
  const [metadataError, setMetadataError] = useState('');
  const generation = useRef(0);
  const params = new URLSearchParams({ view: view === 'favorites' || view === 'trash' ? view : 'library', q: query });
  if (album) params.set('album', album);
  const path = `/photos?${params}`;
  const needsPhotos = album !== null || !['albums', 'places', 'settings'].includes(view);
  useEffect(() => {
    generation.current += 1;
    setMoreBusy(false); setPhotoError('');
    if (!needsPhotos) {
      setPage({ items: [], total: 0, next_cursor: null });
      setPhotoBusy(false);
      return;
    }
    const controller = new AbortController();
    setPhotoBusy(true);
    api<PhotoPage>(path, { signal: controller.signal }).then(page => {
      if (!controller.signal.aborted) setPage(page);
    }).catch(error => {
      if (!controller.signal.aborted) setPhotoError(errorMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setPhotoBusy(false); });
    return () => controller.abort();
  }, [needsPhotos, path, revision]);
  useEffect(() => {
    const controller = new AbortController();
    setMetadataBusy(true); setMetadataError('');
    Promise.all([
      api<Album[]>('/albums', { signal: controller.signal }),
      api<Stats>('/stats', { signal: controller.signal }),
    ]).then(([albums, stats]) => {
      if (!controller.signal.aborted) { setAlbums(albums); setStats(stats); }
    }).catch(error => {
      if (!controller.signal.aborted) setMetadataError(errorMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setMetadataBusy(false); });
    return () => controller.abort();
  }, [revision]);
  const loadMore = useCallback(async () => {
    if (!page.next_cursor || moreBusy) return;
    const current = generation.current;
    setMoreBusy(true);
    try {
      const cursor = encodeURIComponent(page.next_cursor);
      const next = await api<PhotoCursorPage>(`${path}&cursor=${cursor}&include_total=false`);
      if (current === generation.current) {
        setPage(previous => ({
          items: [...previous.items, ...next.items],
          total: previous.total,
          next_cursor: next.next_cursor,
        }));
      }
    } catch (error) { if (current === generation.current) setPhotoError(errorMessage(error)); }
    finally { if (current === generation.current) setMoreBusy(false); }
  }, [moreBusy, page.next_cursor, path]);
  return {
    ...page,
    albums,
    stats,
    busy: photoBusy || (metadataBusy && stats === null),
    moreBusy,
    error: photoError || metadataError,
    loadMore,
  };
}
