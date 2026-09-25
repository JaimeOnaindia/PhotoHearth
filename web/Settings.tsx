import { useState, type FormEvent } from 'react';
import { HardDrive, LockKeyhole, ShieldCheck, Smartphone } from 'lucide-react';
import { api, ApiError, bytes, errorMessage, type Stats } from './api';

export function Settings({ stats, name, csrf, onPasswordChanged }: {
  stats: Stats | null; name: string; csrf: string; onPasswordChanged: () => void;
}) {
  const used = stats ? stats.disk_total - stats.disk_free : 0;
  return <div className="settings-grid"><section className="settings-card wide"><span className="settings-icon"><HardDrive /></span><div><span className="eyebrow">ALMACENAMIENTO LOCAL</span><h2>El espacio de tus recuerdos</h2><p>Los originales se guardan sin modificar en tu servidor.</p></div>
    {stats && <div className="disk-detail"><div><strong>{bytes(stats.original_bytes)}</strong><span>en originales · incluye la papelera</span></div><progress value={used} max={stats.disk_total} aria-label="Espacio ocupado del disco" /><p>{bytes(stats.disk_free)} libres de {bytes(stats.disk_total)} en el disco. El espacio ocupado incluye otros archivos del servidor.</p></div>}
  </section><section className="settings-card"><ShieldCheck className="coral" /><h2>Tu hogar, tus reglas</h2><p>Una biblioteca privada para <strong>{name}</strong>. Solo se accede con tu contraseña y no se envían tus fotos a servicios externos.</p><div className="setting-note"><LockKeyhole size={16} /> Sin enlaces públicos ni rastreadores.</div></section>
    <section className="settings-card"><Smartphone className="coral" /><h2>Llévalo contigo</h2><p>Con una conexión HTTPS, abre el menú de tu navegador y elige «Instalar aplicación» o «Añadir a pantalla de inicio».</p><small>Las subidas necesitan que mantengas la app abierta. Esta versión no hace copias automáticas en segundo plano.</small></section>
    <PasswordForm csrf={csrf} onDone={onPasswordChanged} />
    <section className="settings-card wide"><h2>Un recuerdo merece otra copia</h2><p>Tu servidor es el hogar de las fotos, pero no sustituye una copia de seguridad. La guía del proyecto explica cómo copiar y restaurar la biblioteca completa en otro disco.</p><p className="setting-note">PhotoHearth 0.1 · Hecho para quedarse en casa.</p></section></div>;
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
