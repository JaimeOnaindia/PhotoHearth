import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { FolderInput, HardDrive, LockKeyhole, Pause, Play, RefreshCw, ShieldCheck, Smartphone, XCircle } from 'lucide-react';
import { api, ApiError, bytes, errorMessage, type ImportJob, type ImportList, type Stats } from './api';

export function Settings({ stats, name, csrf, onPasswordChanged }: {
  stats: Stats | null; name: string; csrf: string; onPasswordChanged: () => void;
}) {
  const used = stats ? stats.disk_total - stats.disk_free : 0;
  return <div className="settings-grid"><section className="settings-card wide"><span className="settings-icon"><HardDrive /></span><div><span className="eyebrow">ALMACENAMIENTO LOCAL</span><h2>El espacio de tus recuerdos</h2><p>Los originales se guardan sin modificar en tu servidor.</p></div>
    {stats && <div className="disk-detail"><div><strong>{bytes(stats.original_bytes)}</strong><span>en originales · incluye la papelera</span></div><progress value={used} max={stats.disk_total} aria-label="Espacio ocupado del disco" /><p>{bytes(stats.disk_free)} libres de {bytes(stats.disk_total)} en el disco. El espacio ocupado incluye otros archivos del servidor.</p></div>}
  </section><section className="settings-card"><ShieldCheck className="coral" /><h2>Tu hogar, tus reglas</h2><p>Una biblioteca privada para <strong>{name}</strong>. Solo se accede con tu contraseña y no se envían tus fotos a servicios externos.</p><div className="setting-note"><LockKeyhole size={16} /> Sin enlaces públicos ni rastreadores.</div></section>
    <section className="settings-card"><Smartphone className="coral" /><h2>Llévalo contigo</h2><p>Con una conexión HTTPS, abre el menú de tu navegador y elige «Instalar aplicación» o «Añadir a pantalla de inicio».</p><small>Las subidas necesitan que mantengas la app abierta. Esta versión no hace copias automáticas en segundo plano.</small></section>
    <ServerImports csrf={csrf} />
    <PasswordForm csrf={csrf} onDone={onPasswordChanged} />
    <section className="settings-card wide"><h2>Un recuerdo merece otra copia</h2><p>Tu servidor es el hogar de las fotos, pero no sustituye una copia de seguridad. La guía del proyecto explica cómo copiar y restaurar la biblioteca completa en otro disco.</p><p className="setting-note">PhotoHearth 0.1 · Hecho para quedarse en casa.</p></section></div>;
}

const importLabels: Record<ImportJob['status'], string> = {
  queued: 'En cola', running: 'Importando', paused: 'En pausa', completed: 'Terminada',
  completed_errors: 'Terminada con fallos', canceled: 'Cancelada',
};

function ServerImports({ csrf }: { csrf: string }) {
  const [source, setSource] = useState('.');
  const [imports, setImports] = useState<ImportList | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      setImports(await api<ImportList>('/imports'));
      setError('');
    } catch (error) {
      setError(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const active = imports?.jobs.some(job => ['queued', 'running'].includes(job.status));
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => void refresh(), 2000);
    return () => window.clearInterval(timer);
  }, [active, refresh]);

  function replaceJob(job: ImportJob) {
    setImports(current => current && {
      ...current,
      jobs: [job, ...current.jobs.filter(candidate => candidate.id !== job.id)].slice(0, 20),
    });
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy('create'); setError('');
    try {
      replaceJob(await api<ImportJob>('/imports', {
        method: 'POST', body: JSON.stringify({ source }),
      }, csrf));
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(''); }
  }

  async function control(job: ImportJob, action: 'pause' | 'resume' | 'retry' | 'cancel') {
    if (busy) return;
    setBusy(job.id); setError('');
    try {
      replaceJob(await api<ImportJob>(`/imports/${job.id}/${action}`, { method: 'POST' }, csrf));
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(''); }
  }

  return <section className="settings-card wide import-settings">
    <div className="import-heading"><span className="settings-icon"><FolderInput /></span><div>
      <span className="eyebrow">IMPORTACIÓN MASIVA</span><h2>Traer una carpeta a PhotoHearth</h2>
      <p>Copia tus carpetas al directorio de importación del servidor. El proceso continúa aunque cierres esta página y nunca modifica los archivos de origen.</p>
    </div></div>
    {imports && !imports.enabled ? <p className="import-warning" role="status">La carpeta de importación todavía no está configurada en el servidor.</p> : <form className="import-form" onSubmit={create}>
      <label htmlFor="import-source">Subcarpeta del servidor</label>
      <div><input id="import-source" value={source} maxLength={1024} disabled={busy === 'create'} onChange={event => setSource(event.target.value)} placeholder=". o Viajes/Portugal" /><button className="button primary" disabled={!!busy || imports === null}>{busy === 'create' ? 'Preparando…' : 'Importar carpeta'}</button></div>
      <small>Usa <code>.</code> para importar toda la carpeta configurada. Solo se aceptan rutas relativas.</small>
    </form>}
    {error && <p className="error" role="alert">{error}</p>}
    {imports === null && !error ? <p className="import-loading">Consultando la cola del servidor…</p> : imports?.jobs.length === 0 ? <p className="import-empty">Todavía no hay importaciones. Cuando conectes un disco, podrás iniciarlas desde aquí.</p> : <div className="import-jobs">
      {imports?.jobs.map(job => <article className="import-job" key={job.id}>
        <header><div><strong>{job.source === '.' ? 'Toda la carpeta de importación' : job.source}</strong><span className={`import-status ${job.status}`}>{importLabels[job.status]}</span></div><time dateTime={job.created_at}>{new Date(job.created_at).toLocaleString('es')}</time></header>
        <progress value={job.finished} max={Math.max(job.total, 1)} aria-label={`Progreso de ${job.source}`} />
        <p><strong>{job.finished.toLocaleString('es')} de {job.total.toLocaleString('es')}</strong> revisadas · {job.imported.toLocaleString('es')} nuevas · {job.duplicates.toLocaleString('es')} duplicadas{job.failed > 0 && <> · <span>{job.failed.toLocaleString('es')} con fallo</span></>}</p>
        <div className="import-actions">
          {(['queued', 'running'] as const).includes(job.status as 'queued' | 'running') && <button className="button" disabled={!!busy} onClick={() => void control(job, 'pause')}><Pause size={15} /> Pausar</button>}
          {(['paused', 'canceled'] as const).includes(job.status as 'paused' | 'canceled') && <button className="button" disabled={!!busy} onClick={() => void control(job, 'resume')}><Play size={15} /> Reanudar</button>}
          {job.status === 'completed_errors' && <button className="button" disabled={!!busy} onClick={() => void control(job, 'retry')}><RefreshCw size={15} /> Reintentar fallos</button>}
          {(['queued', 'running', 'paused'] as const).includes(job.status as 'queued' | 'running' | 'paused') && <button className="button subtle" disabled={!!busy} onClick={() => void control(job, 'cancel')}><XCircle size={15} /> Cancelar</button>}
        </div>
      </article>)}
    </div>}
  </section>;
}

function PasswordForm({ csrf, onDone }: { csrf: string; onDone: () => void }) {
  const [current, setCurrent] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    if (password !== confirmation) { setError('Las contraseñas nuevas no coinciden.'); return; }
    setBusy(true); setError('');
    try {
      await api('/auth/password', {
        method: 'POST', body: JSON.stringify({ current_password: current, new_password: password }),
      }, csrf);
      setCurrent(''); setPassword(''); setConfirmation('');
      onDone();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) { onDone(); return; }
      setError(errorMessage(error));
    } finally { setBusy(false); }
  }

  return <section className="settings-card wide">
    <LockKeyhole className="coral" /><h2>Cambiar contraseña</h2>
    <p id="password-change-help">Usa entre 12 y 128 caracteres. Al guardar se cerrarán todas las sesiones, incluida esta. Después entra con tu nueva contraseña.</p>
    <form className="login-form" onSubmit={submit} aria-describedby="password-change-help" aria-busy={busy}>
      <label htmlFor="current-password">Contraseña actual</label>
      <div className="password-input"><input id="current-password" type="password" autoComplete="current-password" required maxLength={128} disabled={busy} value={current} onChange={event => setCurrent(event.target.value)} /></div>
      <label htmlFor="new-password">Nueva contraseña</label>
      <div className="password-input"><input id="new-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} disabled={busy} value={password} onChange={event => setPassword(event.target.value)} /></div>
      <label htmlFor="confirm-password">Repite la nueva contraseña</label>
      <div className="password-input"><input id="confirm-password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} disabled={busy} value={confirmation} onChange={event => setConfirmation(event.target.value)} /></div>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="button primary" disabled={busy}>{busy ? 'Guardando…' : 'Cambiar y cerrar sesiones'}</button>
    </form>
  </section>;
}
