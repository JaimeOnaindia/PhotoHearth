export type User = { name: string; csrf: string };
export type Photo = {
  id: string; filename: string; bytes: number; width: number; height: number;
  taken_at: string; uploaded_at: string; favorite: boolean; deleted_at: string | null;
  latitude: number | null; longitude: number | null; location_name: string | null;
};
export type LocationInput = { latitude: number; longitude: number; name: string };
export type PhotoPatch = { favorite?: boolean; trashed?: boolean; location?: LocationInput | null };
export type Place = { id: string; latitude: number; longitude: number; count: number; cover: string; last_visit: string; name: string | null };
export type PlacePage = { items: Place[]; total: number; located: number; missing: number };
export type Album = { id: string; name: string; created_at: string; count: number; cover: string | null };
export type Stats = {
  photos: number; favorites: number; trash: number; albums: number; original_bytes: number;
  disk_total: number; disk_free: number; max_upload: number;
};
export type PhotoPage = { items: Photo[]; total: number };
export type View = 'library' | 'favorites' | 'albums' | 'trash' | 'settings' | 'places';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}

export async function api<T>(path: string, options: RequestInit = {}, csrf?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...options, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...options.headers },
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new Error('No podemos conectar con tu hogar. Comprueba la conexión y vuelve a intentarlo.');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401 && !path.startsWith('/auth/')) window.dispatchEvent(new Event('session-expired'));
    throw new ApiError(typeof body.detail === 'string' ? body.detail : 'No se pudo completar la operación.', response.status);
  }
  return response.json();
}

export const fileUrl = (id: string, variant: 'thumb' | 'preview' | 'original' = 'thumb') =>
  `/api/photos/${encodeURIComponent(id)}/file?variant=${variant}`;
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'Ha ocurrido un error inesperado.';
export const bytes = (value: number) => {
  if (value < 1024) return `${value} B`;
  const unit = Math.min(Math.floor(Math.log(value) / Math.log(1024)), 4);
  return `${(value / 1024 ** unit).toLocaleString('es', { maximumFractionDigits: 1 })} ${['B', 'KB', 'MB', 'GB', 'TB'][unit]}`;
};
export const dateLabel = (value: string) => new Date(value).toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
