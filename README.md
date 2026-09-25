# PhotoHearth

Biblioteca fotográfica privada para un servidor doméstico. Web responsive con
React y TypeScript; API FastAPI; SQLAlchemy 2 y migraciones Alembic sobre SQLite.
Los originales permanecen en el disco propio y se sirven solo con autenticación.

## Estado de la versión inicial

Cuenta propietaria con contraseña, subida JPEG/PNG/WebP/HEIC, originales intactos,
deduplicación, fecha EXIF, miniaturas, timeline, álbumes, favoritos, búsqueda por
nombre/fecha y papelera recuperable. Exportación de seguridad con prueba de
restauración. No hay borrado definitivo ni limpieza automática de la papelera.

Pendientes: multiusuario, filtro por cámara y copias externas programadas.
Las apps nativas y su subida automática se aplazaron. Mapa GPS, compartir,
búsqueda semántica y reconocimiento facial son fases futuras, no funciones
disponibles. No se incluye soporte de vídeo en esta versión.

## Desarrollo

Requiere Node 22.12+ y Python 3.12. No existen credenciales predeterminadas.

```bash
npm ci
uv sync --frozen --python 3.12
npm run build
.venv/bin/python -m backend.manage create-user --name Jaime
PHOTOHEARTH_SECURE_COOKIE=false PHOTOHEARTH_ORIGINS=http://127.0.0.1:8000 \
  .venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

La excepción HTTP anterior es solo para desarrollo en loopback. En el servidor
se usa HTTPS y cookies Secure.

```bash
.venv/bin/ruff check backend tests migrations
.venv/bin/pytest
npm run typecheck
npm run lint
npx playwright install chromium
npm test
```

Las pruebas de navegador levantan su propia biblioteca temporal; no usan tus
fotos. Guías: [servidor y backups](deploy/DEBIAN.md), [Jenkins](deploy/JENKINS.md).
