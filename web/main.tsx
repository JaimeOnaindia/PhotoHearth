import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/outfit/latin-400.css';
import '@fontsource/outfit/latin-500.css';
import '@fontsource/outfit/latin-600.css';
import { App } from './App';
import { Login } from './Login';
import { api, ApiError, errorMessage, type User } from './api';
import { Brand } from './ui';
import './styles/base.css';
import './styles/layout.css';
import './styles/photos.css';
import './styles/login.css';

function Root() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError('');
    api<User>('/auth/me', { signal: controller.signal }).then(setUser).catch(error => {
      if (!controller.signal.aborted && !(error instanceof ApiError && error.status === 401)) setError(errorMessage(error));
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    const expired = () => setUser(null);
    window.addEventListener('session-expired', expired);
    return () => { controller.abort(); window.removeEventListener('session-expired', expired); };
  }, [retry]);
  if (loading) return <div className="boot-screen"><Brand /><p>Abriendo las puertas de casa…</p></div>;
  if (error) return <div className="boot-screen"><Brand /><h1>Tu hogar está desconectado.</h1><p role="alert">{error}</p><button className="button primary" onClick={() => setRetry(v => v + 1)}>Volver a intentar</button></div>;
  return user ? <App user={user} onLogout={() => setUser(null)} /> : <Login onLogin={setUser} />;
}

createRoot(document.getElementById('root')!).render(<StrictMode><Root /></StrictMode>);
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => { /* The online app remains usable. */ });
}
