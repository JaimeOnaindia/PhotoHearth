import { useEffect, useRef, useState } from 'react';
import { errorMessage } from './api';

type UploadResult = { duplicate: boolean; photo: { deleted_at: string | null } };
type Failure = { file: File; message: string };
export type UploadState = { current: number; total: number; progress: number; name: string; done: boolean; saved: number; duplicates: number; failures: Failure[]; canceled: boolean };

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
        else reject(new Error(typeof body.detail === 'string' ? body.detail : 'No se pudo subir la foto.'));
      } catch { reject(new Error('El servidor no ha respondido correctamente.')); }
    };
    xhr.onerror = () => reject(new Error('Conexión interrumpida. Puedes volver a intentarlo.'));
    xhr.ontimeout = () => reject(new Error('La subida ha tardado demasiado.'));
    xhr.onabort = () => reject(new DOMException('Subida cancelada', 'AbortError'));
    const abort = () => xhr.abort();
    signal.addEventListener('abort', abort, { once: true });
    xhr.onloadend = () => signal.removeEventListener('abort', abort);
    if (signal.aborted) { reject(new DOMException('Subida cancelada', 'AbortError')); return; }
    xhr.send(file);
  });
}

export function useUpload(csrf: string, onDone: () => void) {
  const [state, setState] = useState<UploadState | null>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function upload(files: File[]) {
    if (controller.current || !files.length) return;
    const active = new AbortController(); controller.current = active;
    const result: UploadState = { current: 0, total: files.length, progress: 0, name: '', done: false, saved: 0, duplicates: 0, failures: [], canceled: false };
    setState({ ...result });
    let nextIndex = 0;
    const progresses = files.map(() => 0);
    function report(index: number, progress: number) {
      progresses[index] = progress;
      result.progress = Math.round(progresses.reduce((sum, value) => sum + value, 0) / files.length);
      setState({ ...result });
    }
    async function worker() {
      while (!active.signal.aborted && nextIndex < files.length) {
        const index = nextIndex++;
        result.current = nextIndex; result.name = files[index].name;
        setState({ ...result });
        try {
          if (files[index].size > 40 * 1024 * 1024) throw new Error('Supera el máximo de 40 MB por foto.');
          const uploaded = await send(files[index], csrf, active.signal, progress => report(index, progress));
          if (uploaded.duplicate && uploaded.photo.deleted_at) throw new Error('Ya está en la papelera. Restáurala desde allí.');
          if (uploaded.duplicate) result.duplicates += 1; else result.saved += 1;
        } catch (error) {
          if (active.signal.aborted) break;
          result.failures = [...result.failures, { file: files[index], message: errorMessage(error) }];
        }
        report(index, 100);
      }
    }
    await Promise.all([worker(), worker()]);
    result.done = true; result.canceled = active.signal.aborted; result.progress = 100;
    setState({ ...result }); controller.current = null; onDone();
  }
  return { state, upload, cancel: () => controller.current?.abort(), dismiss: () => setState(null) };
}
