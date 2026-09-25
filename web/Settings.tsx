import { HardDrive, LockKeyhole, ShieldCheck, Smartphone } from 'lucide-react';
import { bytes, type Stats } from './api';

export function Settings({ stats, name }: { stats: Stats | null; name: string }) {
  const used = stats ? stats.disk_total - stats.disk_free : 0;
  return <div className="settings-grid"><section className="settings-card wide"><span className="settings-icon"><HardDrive /></span><div><span className="eyebrow">ALMACENAMIENTO LOCAL</span><h2>El espacio de tus recuerdos</h2><p>Los originales se guardan sin modificar en tu servidor.</p></div>
    {stats && <div className="disk-detail"><div><strong>{bytes(stats.original_bytes)}</strong><span>en originales · incluye la papelera</span></div><progress value={used} max={stats.disk_total} aria-label="Espacio ocupado del disco" /><p>{bytes(stats.disk_free)} libres de {bytes(stats.disk_total)} en el disco. El espacio ocupado incluye otros archivos del servidor.</p></div>}
  </section><section className="settings-card"><ShieldCheck className="coral" /><h2>Tu hogar, tus reglas</h2><p>Una biblioteca privada para <strong>{name}</strong>. Solo se accede con tu contraseña y no se envían tus fotos a servicios externos.</p><div className="setting-note"><LockKeyhole size={16} /> Sin enlaces públicos ni rastreadores.</div></section>
    <section className="settings-card"><Smartphone className="coral" /><h2>Llévalo contigo</h2><p>Con una conexión HTTPS, abre el menú de tu navegador y elige «Instalar aplicación» o «Añadir a pantalla de inicio».</p><small>Las subidas necesitan que mantengas la app abierta. Esta versión no hace copias automáticas en segundo plano.</small></section>
    <section className="settings-card wide"><h2>Un recuerdo merece otra copia</h2><p>Tu servidor es el hogar de las fotos, pero no sustituye una copia de seguridad. La guía del proyecto explica cómo copiar y restaurar la biblioteca completa en otro disco.</p><p className="setting-note">PhotoHearth 0.1 · Hecho para quedarse en casa.</p></section></div>;
}
