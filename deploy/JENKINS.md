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
La producción se actualiza manualmente tras hacer una copia de seguridad.
No permitir a colaboradores no confiables modificar el Jenkinsfile: los
trabajos ejecutan código en el agente. La separación en contenedores no
sustituye un servidor dedicado cuando se incorporan colaboradores externos.

Los navegadores del agente se fijan a la versión de Playwright del lockfile.
Al actualizar Playwright, actualizar también `deploy/jenkins/agent.Dockerfile`
y reconstruir el agente. Revisar periódicamente versiones e informes de
seguridad de Jenkins, plugins y dependencias; las imágenes no se autoactualizan.

## Estado inicial (25 de septiembre de 2026)

Código publicado en `main` con autorización del propietario, sin contraseñas,
claves privadas ni fotos. La ejecución #1 del trabajo PhotoHearth descargó el
commit `a313ffe` desde GitHub y terminó con `SUCCESS` en unos 55 segundos:
once pruebas de backend y cuatro de navegador, sin fallos ni pruebas omitidas.
Jenkins publicó los resultados JUnit y `photohearth-source.tar.gz`.

La consulta automática de cambios queda activada cada cinco minutos. Esto
ejecuta las comprobaciones y genera el artefacto; no modifica producción.
