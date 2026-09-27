# Operación del servidor Xiaomi

## Servidor instalado

El propietario instaló Debian. Se verificó por SSH el Xiaomi Timi TM1703,
con Debian 13.7, 8 GB de RAM y SSD NVMe de 256 GB. Docker y Compose están
instalados y Docker arranca automáticamente. Hay acceso SSH con una clave
dedicada; no se ha desactivado el acceso administrativo existente.

El despliegue está en `/home/james/photohearth`. La configuración privada `.env`
selecciona la dirección LAN. Conviene reservar esa IP en el DHCP del router.
No se abren puertos del router. Las apps Android/iOS y la subida automática
permanecen aplazadas.

## Operación

Desde el directorio del proyecto en el servidor:

Antes del primer arranque PostgreSQL, preparar el secreto y seguir
[la guía de migración](POSTGRES.md). No reutilizar directamente el volumen SQLite.

```bash
sudo docker compose -f compose.yaml -f compose.ci.yaml up -d --build
sudo docker compose -f compose.yaml -f compose.ci.yaml ps
sudo docker compose logs --tail=100 app gateway
sudo docker compose exec app python -m backend.manage reset-password
```

No usar `down -v`: elimina los volúmenes con fotos, base de datos y Jenkins.
No hay despliegues automáticos de producción desde Jenkins.

### Importación desde disco

El directorio `imports` del despliegue se monta como `/imports` dentro de la
aplicación en modo de solo lectura. Prepararlo antes de arrancar y copiar allí
las carpetas que se quieran incorporar:

```bash
install -d -m 750 /home/james/photohearth/imports
cp -R /ruta/del/disco/Viaje /home/james/photohearth/imports/
chgrp -R "$(id -g)" /home/james/photohearth/imports
find /home/james/photohearth/imports -type d -exec chmod 750 {} +
find /home/james/photohearth/imports -type f -exec chmod 640 {} +
```

Si el disco se va a leer directamente, establecer su punto de montaje mediante
`PHOTOHEARTH_IMPORTS=/ruta/del/disco` y el resultado de `id -g` como
`PHOTOHEARTH_IMPORT_GID` en `.env`. El contenedor nunca recibe
permiso de escritura sobre esa ruta. Desde «Mi hogar» se usa `.` para toda la
carpeta o una ruta relativa como `Viaje/Portugal`. Los archivos de origen no se
mueven ni se borran; pueden retirarse cuando el trabajo termine.

### HTTPS doméstico

Caddy emite certificados mediante una autoridad local. Exportar únicamente su
certificado público (nunca la clave privada) e importarlo como autoridad de
confianza en los dispositivos propios que vayan a acceder:

```bash
sudo docker compose cp gateway:/data/caddy/pki/authorities/local/root.crt ./photohearth-ca.crt
```

No basta con HTTPS para un acceso desde Internet: mantener los servicios en la
LAN. El acceso remoto mediante VPN necesita una configuración adicional.

## Copia y restauración

Exportar una instantánea coherente mientras la aplicación está funcionando:

```bash
umask 077
sudo docker compose exec -T app python -m backend.backup > photohearth-backup.tar.partial
mv photohearth-backup.tar.partial photohearth-backup.tar
tar -tf photohearth-backup.tar
```

Ejecutar el `mv` solo si el comando de exportación termina correctamente. Copiar
el archivo a otro dispositivo: una copia en el mismo SSD no protege de su avería.
El archivo contiene fotos y el hash de la contraseña; guardarlo en un destino
cifrado y privado. No incluye contraseñas de Jenkins, certificados ni claves SSH.
Las sesiones se excluyen para exigir un nuevo inicio de sesión al restaurar.

La copia PostgreSQL contiene `database.dump` y los archivos de imágenes.
Seguir [la restauración PostgreSQL](POSTGRES.md). Las copias antiguas contienen
`library.sqlite3` y requieren la versión SQLite para restaurar la biblioteca completa.
Nunca extraer un tar desconocido como root ni restaurar encima de una biblioteca activa.

La programación de copias externas queda pendiente de elegir un destino.
