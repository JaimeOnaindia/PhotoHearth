import { AlertCircle, CheckCircle2, Upload, X } from 'lucide-react';
import type { UploadState } from './useUpload';

export function UploadPanel({ state, onCancel, onDismiss, onRetry }: {
  state: UploadState; onCancel: () => void; onDismiss: () => void; onRetry: (files: File[]) => void;
}) {
  return <aside className="upload-panel" aria-label="Estado de las subidas"><header><span className="upload-icon">{state.done ? (state.failures.length ? <AlertCircle size={20} /> : <CheckCircle2 size={20} />) : <Upload size={20} />}</span><strong>{state.done ? (state.canceled ? 'Subida detenida' : state.failures.length ? 'Subida con pendientes' : 'Subida terminada') : `Procesadas ${state.current} de ${state.total}`}</strong>
    <button className="icon-button" aria-label={state.done ? 'Cerrar subidas' : 'Cancelar subidas'} onClick={state.done ? onDismiss : onCancel}><X size={18} /></button></header>
    <div className="upload-content" aria-live="polite">{state.done ? <p>{state.saved} guardadas · {state.duplicates} ya estaban en casa{state.failures.length > 0 ? ` · ${state.failures.length} pendientes` : ''}</p> : <><p className="truncate">{state.name}</p><progress max={100} value={state.progress} aria-label="Progreso de subida" /><small>{state.progress === 100 ? 'Preparando la miniatura…' : `${state.progress}% · Mantén esta ventana abierta`}</small></>}
    {state.stopReason && <p role="alert">{state.stopReason} La cola se ha detenido; puedes reintentar los pendientes.</p>}
    {!state.done && <small>Se envían como máximo dos fotos a la vez. En el móvil, mantén esta pestaña visible. Si el selector se bloquea antes de empezar, selecciona lotes más pequeños.</small>}
    {state.done && state.failures.length > 0 && <button className="button" onClick={() => onRetry(state.failures.map(f => f.file))}>Reintentar pendientes</button>}
    {state.failures.length > 0 && <details open={state.done}><summary>Archivos pendientes ({state.failures.length})</summary><ul>{state.failures.slice(0, 20).map(({ file, message }, i) => <li key={i}><strong>{file.name}</strong><span>{message}</span></li>)}</ul>{state.failures.length > 20 && <small>Mostrando 20 de {state.failures.length}. El reintento incluye todos los pendientes.</small>}</details>}
    {state.canceled && <small>Las fotos que ya se guardaron siguen en tu biblioteca. Puedes volver a seleccionar los archivos; los duplicados se omiten.</small>}</div>
  </aside>;
}
