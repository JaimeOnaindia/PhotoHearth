# Xiaomi como servidor de PhotoHearth

Destino: el portátil Xiaomi del propietario. El equipo de trabajo actual es un
Lenovo y no debe reinstalarse. Un cable USB entre ambos portátiles no proporciona
acceso al disco del Xiaomi ni permite controlar su instalador.

## Imagen preparada

- Debian 13.7.0 `amd64 netinst`, desde el servidor oficial de Debian.
- Ruta local: `data/installers/debian-13.7.0/debian-13.7.0-amd64-netinst.iso`.
- El directorio contiene también `SHA512SUMS`, su firma y la clave pública de Debian.
- Huella de la clave de firma: `DF9B 9C49 EAA9 2984 3258 9D76 DA87 E80D 6294 BE9B`.
- Las imágenes y claves descargadas están excluidas de Git mediante `data/`.

Comprobar desde el directorio de descarga:

```bash
gpgv --keyring ./debian-cd-key.gpg SHA512SUMS.sign SHA512SUMS
sha512sum --check --ignore-missing SHA512SUMS
```

Referencias: [instalador oficial](https://www.debian.org/releases/stable/debian-installer/)
y [verificación de Debian](https://www.debian.org/CD/verify).

## Instalación mínima

1. Preparar un pendrive de al menos 2 GB. Antes de grabarlo, identificar modelo,
   capacidad y número de serie, y comprobar si contiene archivos. La autorización
   para borrar el Xiaomi no supone autorización para borrar otro dispositivo.
2. Arrancar el Xiaomi desde ese pendrive usando su menú de arranque UEFI.
   La tecla concreta se comprobará con el modelo exacto del portátil.
3. Conectar el Xiaomi a la red doméstica. Ethernet con adaptador USB es una opción
   si la Wi-Fi no está disponible durante la instalación.
4. Elegir idioma, teclado y zona horaria `Europe/Madrid`. Nombre del equipo:
   `photohearth`.
5. Crear el usuario administrador durante el instalador. Introducir las contraseñas
   directamente allí, sin guardarlas en este repositorio ni enviarlas por el chat.
   Dejar vacía la contraseña de root permite administrar mediante sudo con el
   primer usuario, según el instalador de Debian.
6. Antes del particionado, identificar el disco interno del Xiaomi. El usuario ha
   autorizado borrar su contenido, pero no se ha identificado aún ese disco.
   El pendrive instalador y el disco del Lenovo quedan fuera del borrado autorizado.
7. En la selección de software, marcar **servidor SSH** y **utilidades estándar
   del sistema**. Desmarcar **entorno de escritorio Debian** y todos los escritorios.
8. Al terminar, retirar el pendrive y arrancar Debian. Obtener la dirección local
   con `hostname -I` y comprobar el acceso SSH desde el Lenovo.

Referencia: [componentes del instalador](https://www.debian.org/releases/stable/amd64/ch06s03.en.html).

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

```bash
sudo docker compose -f compose.yaml -f compose.ci.yaml up -d --build
sudo docker compose -f compose.yaml -f compose.ci.yaml ps
sudo docker compose logs --tail=100 app gateway
sudo docker compose exec app python -m backend.manage reset-password
```

No usar `down -v`: elimina los volúmenes con fotos, base de datos y Jenkins.
No hay despliegues automáticos de producción desde Jenkins.

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

Para restaurar: detener la app, extraer una copia propia verificada en un
directorio **nuevo y vacío**, asignar propietario `10001:10001`, definir
`PHOTOHEARTH_STORAGE` con esa ruta absoluta y arrancar la app. Conservar el
volumen anterior hasta verificar fotos, álbumes y login. Nunca extraer un tar
desconocido como root ni restaurar encima de una biblioteca activa.

La programación de copias externas queda pendiente de elegir un destino.

## Verificación del primer despliegue (25 de septiembre de 2026)

PhotoHearth y Jenkins responden por HTTPS en la LAN con certificado local
validado. Se comprobó el login de la biblioteca y el rechazo de accesos anónimos.
El controlador tiene cero ejecutores y el agente uno, conectado. Pasaron once
pruebas de backend y cuatro de navegador dentro del agente del Xiaomi.
Se exportó una primera copia de la biblioteca vacía, también al equipo de trabajo.
Las actualizaciones automáticas de Debian están habilitadas y se instaló el
ajuste para no suspender al cerrar la tapa. Mantener el portátil bien ventilado.
