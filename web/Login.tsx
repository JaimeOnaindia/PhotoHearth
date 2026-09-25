import { useState, type FormEvent } from 'react';
import { ArrowRight, Eye, EyeOff, HardDrive, LockKeyhole, ShieldCheck } from 'lucide-react';
import { api, errorMessage, type User } from './api';
import { Brand, Landscape } from './ui';

export function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [password, setPassword] = useState('');
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('');
    try { onLogin(await api<User>('/auth/login', { method: 'POST', body: JSON.stringify({ password }) })); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <main className="login-page"><section className="login-form-side"><Brand />
    <div className="login-content"><span className="eyebrow"><span className="status-dot" /> UN ESPACIO SOLO TUYO</span>
      <h1>Lo que importa,<br />se queda en casa<span className="coral">.</span></h1>
      <p>Tus viajes, tus personas, tus pequeños momentos.<br className="desktop-only" /> Todos juntos. Siempre tuyos.</p>
      <form onSubmit={submit} className="login-form"><label htmlFor="password">Contraseña de tu hogar</label>
        <div className="password-input"><LockKeyhole size={18} /><input id="password" type={visible ? 'text' : 'password'}
          autoComplete="current-password" required maxLength={128} value={password} onChange={e => setPassword(e.target.value)} placeholder="Introduce tu contraseña" />
          <button type="button" className="icon-button" aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button>
        </div>{error && <p className="error" role="alert">{error}</p>}
        <button className="button primary" disabled={busy}>{busy ? 'Abriendo tu hogar…' : 'Entrar a mi biblioteca'}<ArrowRight size={18} /></button>
      </form><p className="login-help">¿Es tu primera vez? La cuenta se crea al configurar tu servidor. Tu contraseña nunca viene predefinida.</p>
    </div><footer><ShieldCheck size={17} /> Privado por naturaleza. Alojado por ti.</footer>
    </section><section className="login-art" aria-label="Tus recuerdos tienen un hogar"><div className="art-caption">LA VIDA PASA.<br /><span>Los recuerdos se quedan.</span></div>
      <div className="login-polaroid one"><Landscape variant={1} /><span>un lugar al que volver</span></div>
      <div className="login-polaroid two"><Landscape /><span>sin prisa, sin filtros.</span></div>
      <span className="login-spark">✳</span><div className="local-badge"><span><HardDrive size={20} /></span><div>Un hogar para tus fotos<small>Sin nubes ajenas. Sin suscripciones.</small></div></div>
    </section></main>;
}
