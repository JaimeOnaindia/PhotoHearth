# PostgreSQL y migración limpia

Producción usa PostgreSQL 17 en una red Docker interna, sin puerto público.
La base vive en `postgres_data`; las imágenes en `photohearth_data_pg`.
SQLAlchemy y Alembic mantienen los modelos y el esquema. La web sube dos archivos
en paralelo; PostgreSQL elimina la serialización de escrituras propia de SQLite,
pero la velocidad también depende de CPU, disco y generación de miniaturas.

## Preparación

Generar un secreto aleatorio **solo en el servidor**, fuera de Git:

```bash
install -d -m 700 data/deployment
openssl rand -hex 32 > data/deployment/postgres-password
chmod 644 data/deployment/postgres-password
```

No ejecutar de nuevo si el secreto ya existe. El directorio 700 impide acceso a
otros usuarios del host; el archivo debe ser legible por los UID distintos de
la app y PostgreSQL al montarse como secreto de Compose. No copiarlo a repositorios.

## Migración desde SQLite

Esta migración es **owner-only**: conserva nombre y hash de contraseña, pero inicia
una biblioteca vacía, sin fotos ni álbumes. Es la opción acordada para esta instalación
con una sola foto. No sirve para migrar una biblioteca completa sin perder su catálogo.

1. Conservar el código/imagen anteriores y detener las subidas.
2. Exportar con `python -m backend.backup` usando la imagen SQLite anterior.
   Verificar el tar y guardarlo también fuera del servidor.
3. Conservar el volumen SQLite anterior sin modificarlo. Extraer `library.sqlite3`
   del backup a un directorio privado y montar ese archivo como solo lectura.
4. Arrancar únicamente `db` con el nuevo Compose y esperar a que esté saludable.
5. Con el nuevo contenedor app, ejecutar:

```bash
sudo docker compose run --rm --no-deps \
  -v /ruta/privada/library.sqlite3:/legacy/library.sqlite3:ro app \
  python -m backend.migrate_sqlite --source /legacy/library.sqlite3 --owner-only
```

El UID 10001 debe poder leer el archivo montado. El importador rechaza destinos
que ya contienen usuarios, fotos o álbumes. Después arrancar app y gateway,
comprobar login, estado y biblioteca vacía. No ejecutar `down -v`.

Para volver atrás: detener la app nueva y arrancar el código/imagen SQLite anteriores
con el volumen anterior. No reutilizar el volumen PostgreSQL para ello. Las fotos
subidas después del cambio no aparecerán en la biblioteca SQLite de respaldo.

## Backup y restauración PostgreSQL

`python -m backend.backup` exporta un tar con `database.dump`, `originals/`,
`previews/` (miniaturas y vistas previas). Usa una instantánea compartida entre el catálogo y
`pg_dump`; excluye sesiones y contadores de login. Los originales son inmutables.
El cliente `pg_dump` incluido es de la versión 17. El dump temporal debe caber en
el `/tmp` del contenedor (128 MiB por defecto; ampliar para catálogos grandes).

Restaurar siempre en **una base nueva vacía y un directorio nuevo**:

1. Extraer un backup propio verificado como usuario sin privilegios.
2. Copiar `originals/` y `previews/` al nuevo almacenamiento y asignar
   propietario `10001:10001`. No copiar `database.dump` al directorio servido.
3. Con la app detenida, restaurar el dump en el PostgreSQL nuevo:
   `pg_restore --no-owner --no-acl --dbname=BASE_NUEVA database.dump`.
   Usar cliente 17 o posterior y pasar credenciales por archivo protegido/entorno,
   nunca incorporarlas a comandos guardados ni al repositorio.
4. Configurar app para la base y almacenamiento restaurados; arrancar y verificar
   login, álbumes, originales y miniaturas antes de retirar la copia anterior.

Las pruebas automatizadas restauran en un esquema temporal aislado. No prueban
ni reemplazan la recuperación física del portátil. Las copias externas programadas
siguen pendientes de elegir destino.

## Ubicación y privacidad

La sección Lugares agrupa fotos cercanas (celdas de 0,01 grados), no identifica
ciudades automáticamente. Permite consultar hasta 500 zonas y filtrar sus fotos.
El visor permite añadir, corregir o quitar coordenadas y dar nombre al lugar.
Cambiar esa información no modifica el EXIF del original descargable.

OpenStreetMap solo recibe solicitudes de mapas tras pulsar «Activar mapa»:
puede ver la IP y el área visualizada, pero no las fotos. No se usa geocodificación
externa. Las pruebas del navegador simulan los mapas sin consultar el proveedor.
