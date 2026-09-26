import { useEffect, useRef, useState } from 'react';
import { api, ApiError, errorMessage } from './api';

type UploadResult = { duplicate: boolean; photo: { id: string; deleted_at: string | null } };
type Failure = { file: File; message: string };
export type UploadState = { current: number; total: number; progress: number; name: string; done: boolean; saved: number; duplicates: number; failures: Failure[]; canceled: boolean; albumId: string | null; stopReason: string };

function send(file: File, csrf: string, signal: AbortSignal, progress: (percent: number) => void): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/api/photos/upload?filename=${encodeURIComponent(file.name)}`);
    xhr.setRequestHeader('X-CSRF-Token', csrf);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.timeout = 180_000;
    xhr.upload.onprogress = e => { if (e.lengthComputable) progress(Math.round(e.loaded / e.total * 100)); };
    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status === 401) window.dispatchEvent(new Event('session-expired'));
        if (xhr.status >= 200 && xhr.status < 300) resolve(body);
        else reject(new ApiError(typeof body.detail === 'string' ? body.detail : 'No se pudo subir la foto.', xhr.status));
      } catch { reject(new ApiError('El servidor no ha respondido correctamente.', xhr.status || 0)); }
    };
    xhr.onerror = () => reject(new ApiError('Conexión interrumpida. Puedes volver a intentarlo.', 0));
    xhr.ontimeout = () => reject(new ApiError('La subida ha tardado demasiado.', 408));
    xhr.onabort = () => reject(new DOMException('Subida cancelada', 'AbortError'));
    const abort = () => xhr.abort();
    signal.addEventListener('abort', abort, { once: true });
    xhr.onloadend = () => signal.removeEventListener('abort', abort);
    if (signal.aborted) { signal.removeEventListener('abort', abort); reject(new DOMException('Subida cancelada', 'AbortError')); return; }
    try { xhr.send(file); }
    catch (error) { signal.removeEventListener('abort', abort); reject(error); }
  });
}

export function useUpload(csrf: string, onDone: () => void) {
  const [state, setState] = useState<UploadState | null>(null);
  const controller = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; controller.current?.abort(); }; }, []);
  async function upload(files: File[], albumId: string | null = null) {
    if (controller.current || !files.length) return;
    const active = new AbortController(); controller.current = active;
    const result: UploadState = { current: 0, total: files.length, progress: 0, name: '', done: false, saved: 0, duplicates: 0, failures: [], canceled: false, albumId, stopReason: '' };
    setState({ ...result });
    let nextIndex = 0;
    let progressSum = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const progresses = files.map(() => 0);
    const settled = new Set<number>();
    function publish() {
      if (timer !== undefined || !mounted.current) return;
      timer = setTimeout(() => {
        timer = undefined;
        if (mounted.current) setState({ ...result, failures: [...result.failures] });
      }, 200);
    }
    function report(index: number, progress: number) {
      progressSum += progress - progresses[index];
      progresses[index] = progress;
      result.progress = Math.floor(progressSum / files.length);
      publish();
    }
    async function worker() {
      while (!active.signal.aborted && nextIndex < files.length) {
        const index = nextIndex++;
        result.name = files[index].name;
        publish();
        try {
          if (files[index].size > 40 * 1024 * 1024) throw new Error('Supera el máximo de 40 MB por foto.');
          const uploaded = await send(files[index], csrf, active.signal, progress => report(index, progress * 0.9));
          if (uploaded.duplicate && uploaded.photo.deleted_at) throw new Error('Ya está en la papelera. Restáurala desde allí.');
          if (albumId) {
            try { await api(`/albums/${encodeURIComponent(albumId)}/photos/${encodeURIComponent(uploaded.photo.id)}`, { method: 'PUT', signal: active.signal }, csrf); }
            catch (error) {
              if (!active.signal.aborted) result.stopReason = `La foto está guardada, pero no se pudo añadir al álbum: ${errorMessage(error)}`;
              throw error;
            }
          }
          if (uploaded.duplicate) result.duplicates += 1; else result.saved += 1;
        } catch (error) {
          if (active.signal.aborted) break;
          result.failures.push({ file: files[index], message: errorMessage(error) });
          if (result.stopReason || error instanceof ApiError && (error.status === 0 || error.status === 401 || error.status === 403 || error.status === 408 || error.status === 429 || error.status >= 500)) {
            result.stopReason ||= errorMessage(error);
            active.abort();
          }
        }
        settled.add(index);
        result.current += 1;
        report(index, 100);
      }
    }
    await Promise.all([worker(), worker()]);
    if (timer !== undefined) clearTimeout(timer);
    // Keep unstarted and interrupted files available for retry, including duplicates
    // whose first request may have reached the server before the connection dropped.
    for (let index = 0; index < files.length; index += 1) {
      if (!settled.has(index)) result.failures.push({ file: files[index], message: 'Pendiente de subir o confirmar.' });
    }
    result.done = true; result.canceled = active.signal.aborted;
    controller.current = null;
    if (mounted.current) { setState({ ...result }); onDone(); }
  }
  return { state, upload, cancel: () => controller.current?.abort(), dismiss: () => setState(null) };
}
