import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage, type Album, type PhotoPage, type Stats, type View } from './api';

export function useLibrary(view: View, query: string, album: string | null, revision: number) {
  const [page, setPage] = useState<PhotoPage>({ items: [], total: 0 });
  const [albums, setAlbums] = useState<Album[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [busy, setBusy] = useState(true);
  const [moreBusy, setMoreBusy] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const params = new URLSearchParams({ view: view === 'favorites' || view === 'trash' ? view : 'library', q: query });
  if (album) params.set('album', album);
  const path = `/photos?${params}`;
  useEffect(() => {
    const controller = new AbortController();
    generation.current += 1;
    setBusy(true); setError(''); setMoreBusy(false);
    Promise.all([
      api<PhotoPage>(path, { signal: controller.signal }),
      api<Album[]>('/albums', { signal: controller.signal }),
      api<Stats>('/stats', { signal: controller.signal }),
    ]).then(([page, albums, stats]) => {
      if (!controller.signal.aborted) { setPage(page); setAlbums(albums); setStats(stats); }
    }).catch(error => {
      if (!controller.signal.aborted) setError(errorMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [path, revision]);
  const loadMore = useCallback(async () => {
    const current = generation.current;
    setMoreBusy(true);
    try {
      const next = await api<PhotoPage>(`${path}&offset=${page.items.length}`);
      if (current === generation.current) setPage(previous => ({ ...next, items: [...previous.items, ...next.items] }));
    } catch (error) { if (current === generation.current) setError(errorMessage(error)); }
    finally { if (current === generation.current) setMoreBusy(false); }
  }, [path, page.items.length]);
  return { ...page, albums, stats, busy, moreBusy, error, loadMore };
}
