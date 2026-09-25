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

Controlador y agente instalados, conectados y comprobados. Jenkins valida la
sintaxis del Jenkinsfile. Todos los comandos de calidad y pruebas pasaron al
ejecutarlos directamente en el agente. El repositorio GitHub aún está vacío:
la publicación del código espera confirmación del propietario, por lo que no
se ha ejecutado todavía el trabajo completo con checkout desde GitHub.
