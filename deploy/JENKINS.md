# Jenkins privado

El controlador usa Jenkins LTS con Java 21 y cero ejecutores. Un agente separado
ejecuta un único trabajo a la vez. Ninguno monta el socket Docker ni el volumen
de fotos. El agente no recibe credenciales de administración del servidor.
Referencia: [aislamiento del controlador](https://www.jenkins.io/doc/book/security/controller-isolation/).

Arranque: `sudo docker compose -f compose.yaml -f compose.ci.yaml up -d --build`.
La contraseña inicial se lee de `data/deployment/jenkins-password`, excluido de
Git. El usuario es `jaime`. El acceso anónimo está deshabilitado y se mantiene
la protección CSRF. El acceso web es HTTPS en el puerto LAN 8443.

El trabajo `PhotoHearth` carga `Jenkinsfile` desde `main` del repositorio GitHub.
Tras su primera ejecución, consulta cambios cada cinco minutos: no necesita un
webhook público. Si el repositorio se hace privado, será necesario configurar
una credencial de lectura y actualizar el SCM del trabajo.

La pipeline instala dependencias fijadas por los lockfiles, ejecuta Ruff,
TypeScript, ESLint, pytest (incluye migraciones y restauración), compila la web
y prueba los flujos de navegador en escritorio y móvil. Publica resultados
JUnit y un tar del código identificado por commit. Conserva diez ejecuciones
y los artefactos de las tres últimas. Un fallo impide generar el artefacto.

La suite de API y migraciones se ejecuta contra SQLite y PostgreSQL 17. El servicio
`ci-db` es temporal y aislado, sin puertos publicados ni datos de producción.
El agente incluye el cliente PostgreSQL 17 para probar exportación y restauración.
Antes de publicar este Jenkinsfile en una instalación antigua, reconstruir
`ci-agent` y arrancar `ci-db` con ambos archivos Compose. Su contraseña fija es
exclusivamente de pruebas; producción utiliza un secreto diferente.

El artefacto es código listo para construir, no una imagen Docker ya publicada.
`PhotoHearth Deploy` es otra pipeline, de ejecución manual. Lanza `PhotoHearth`,
espera a que pase y despliega exactamente el tar de esa ejecución. El parámetro
`DRY_RUN` comprueba el paquete y el acceso sin modificar producción. No hay
despliegue automático al cambiar `main`.

### Acceso limitado para desplegar

La clave de despliegue permite solamente el comando fijo
`/usr/local/sbin/photohearth-release`; no abre una sesión de shell. Jenkins la
guarda como credencial `photohearth-deploy` y la entrega al agente únicamente
durante esa etapa. El agente sigue sin montar el socket Docker. El comando del
servidor es propiedad de root y `sudoers` autoriza solo ese comando sin contraseña.

En el servidor, desde `/home/james/photohearth`, instalar una vez:

```bash
ssh-keygen -q -t ed25519 -N '' -f data/deployment/jenkins-deploy-key
sudo install -o root -g root -m 755 deploy/jenkins/remote_release.sh /usr/local/sbin/photohearth-release
sudo visudo -cf deploy/jenkins/photohearth-deploy.sudoers
sudo install -o root -g root -m 440 deploy/jenkins/photohearth-deploy.sudoers /etc/sudoers.d/photohearth-deploy
awk '{print "restrict,command=\"sudo -n /usr/local/sbin/photohearth-release\" " $0}' data/deployment/jenkins-deploy-key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
sudo docker compose -f compose.yaml -f compose.ci.yaml build jenkins ci-agent
sudo docker compose -f compose.yaml -f compose.ci.yaml up -d --no-deps --wait jenkins ci-agent
```

`deploy/jenkins/known_hosts` fija la clave pública SSH del servidor. Si cambia,
comprobar la nueva huella antes de actualizar ese archivo. El script recibe el
SHA y el hash del tar, limita su tamaño, rechaza rutas peligrosas, guarda una
copia de seguridad antes de aplicar cambios y recrea solo `app`. Verifica salud,
migración y acceso privado; conserva la copia previa y el paquete si falla.
Las copias quedan en el SSD del servidor: siguen necesitando una copia externa
para protegerse de una avería física. Tras modificar `remote_release.sh`, volver
a instalarlo como root; un despliegue de código no reemplaza ese comando fijo.

No permitir a colaboradores no confiables modificar el Jenkinsfile: los
trabajos ejecutan código en el agente. La separación en contenedores no
sustituye un servidor dedicado cuando se incorporan colaboradores externos.

Los navegadores del agente se fijan a la versión de Playwright del lockfile.
Al actualizar Playwright, actualizar también `deploy/jenkins/agent.Dockerfile`
y reconstruir el agente. Revisar periódicamente versiones e informes de
seguridad de Jenkins, plugins y dependencias; las imágenes no se autoactualizan.
