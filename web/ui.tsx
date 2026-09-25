import { useEffect, useRef, type ReactNode } from 'react';
import { ArrowUpRight, Flower2, LockKeyhole, X } from 'lucide-react';

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className="brand"><span className="brand-icon"><Flower2 size={26} strokeWidth={1.65} /></span>
    {!compact && <span>Photo<span className="brand-light">Hearth</span><small>TUS FOTOS, EN CASA</small></span>}</div>;
}

export function Landscape({ variant = 0 }: { variant?: number }) {
  const palettes = [['#e9c8a6', '#f4e6c9', '#8f9c7c', '#516a58'], ['#cddbd8', '#fbf4dd', '#7e9b90', '#365a55'], ['#e9cbb9', '#f9e5c4', '#b88168', '#775b4d']];
  const [sky, sun, mountain, land] = palettes[variant % 3];
  return <svg viewBox="0 0 320 360" role="img" aria-label="Illustration de paysage" preserveAspectRatio="xMidYMid slice">
    <rect width="320" height="360" fill={sky} /><circle cx="235" cy="92" r="37" fill={sun} />
    <path d="M0 230 87 111 176 235 236 161 320 264V360H0Z" fill={mountain} />
    <path d="M0 282Q84 221 166 283T320 245V360H0Z" fill={land} />
    <path d="M165 360Q239 321 206 296T222 251Q181 289 170 300T102 360Z" fill={sky} opacity=".7" />
  </svg>;
}

export function EmptyState({ title, text, action }: { title: string; text: string; action?: () => void }) {
  return <div className="empty-state"><div className="empty-art" aria-hidden="true">
    <div className="paper-photo back"><Landscape variant={2} /></div>
    <div className="paper-photo front"><Landscape variant={1} /><span>momentos que se quedan.</span></div>
    <span className="art-flower">✳</span></div><h2>{title}</h2><p>{text}</p>
    {action && <button className="button primary" onClick={action}>Añadir mis primeras fotos <ArrowUpRight size={17} /></button>}
    <span className="private-note"><LockKeyhole size={13} /> Solo tú. Solo en tu servidor.</span>
  </div>;
}

export function Modal({ title, children, onClose, className = '' }: {
  title: string; children: ReactNode; onClose: () => void; className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = ref.current!;
    element.showModal();
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { element.close(); document.body.style.overflow = previous; };
  }, []);
  return <dialog ref={ref} className={`modal ${className}`} aria-label={title}
    onCancel={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="modal-inner"><button className="icon-button modal-close" aria-label="Cerrar" onClick={onClose}><X size={21} /></button>
      {children}
    </div>
  </dialog>;
}
