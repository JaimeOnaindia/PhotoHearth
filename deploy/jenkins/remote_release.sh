#!/usr/bin/env bash
set -euo pipefail

# Installed root-owned as /usr/local/sbin/photohearth-release. The SSH key can
# invoke only this command; its input is one header line followed by a CI tarball.
read -r action revision digest
[[ $action == check || $action == deploy ]] || exit 2
[[ $revision =~ ^[0-9a-f]{40}$ ]] || exit 2
[[ $digest =~ ^[0-9a-f]{64}$ ]] || exit 2

cd /home/james/photohearth
umask 077
exec 9>data/deployment/deploy.lock
flock -n 9 || { echo 'Ya hay un despliegue en curso.' >&2; exit 1; }
archive=$(mktemp data/deployment/release.XXXXXXXX.tar.gz)
cleanup() {
    result=$?
    if ((result == 0)); then
        rm -f "$archive"
    else
        printf 'Despliegue fallido; paquete conservado en %s\n' "$archive" >&2
    fi
}
trap cleanup EXIT

# Cap the upload before inspecting it. Source archives are currently under 10 MiB.
head -c 67108865 > "$archive"
(( $(stat -c %s "$archive") <= 67108864 )) || { echo 'Paquete demasiado grande.' >&2; exit 1; }
printf '%s  %s\n' "$digest" "$archive" | sha256sum --check --status
python3 - "$archive" <<'PY'
import sys
import tarfile
from pathlib import PurePosixPath

with tarfile.open(sys.argv[1], 'r:gz') as source:
    members = source.getmembers()
    if len(members) > 1000 or sum(member.size for member in members) > 128 * 1024 * 1024:
        raise SystemExit('Paquete demasiado grande al descomprimir.')
    for member in members:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or '..' in path.parts
            or not path.parts
            or path.parts[0] in {'.env', '.git', '.venv', 'data', 'dist', 'node_modules'}
            or not (member.isfile() or member.isdir())
        ):
            raise SystemExit('Ruta no permitida en el paquete.')
PY

docker compose config --quiet
[[ $(docker inspect --format '{{.State.Health.Status}}' photohearth-db-1) == healthy ]]
[[ $(docker inspect --format '{{.State.Health.Status}}' photohearth-app-1) == healthy ]]
if [[ $action == check ]]; then
    printf 'Paquete %s validado; producción sana. Sin cambios.\n' "$revision"
    exit 0
fi
if [[ -f data/deployment/deployed-sha ]] &&
    [[ $(<data/deployment/deployed-sha) == "$revision" ]]; then
    printf 'El commit %s ya está desplegado.\n' "$revision"
    exit 0
fi

db_started=$(docker inspect --format '{{.State.StartedAt}}' photohearth-db-1)
gateway_started=$(docker inspect --format '{{.State.StartedAt}}' photohearth-gateway-1)
backup="data/deployment/pre-${revision:0:7}-$(date -u +%Y%m%dT%H%M%SZ).tar"
docker compose exec -T app python -m backend.backup > "$backup.partial"
tar -tf "$backup.partial" >/dev/null
mv "$backup.partial" "$backup"
printf 'Copia previa validada: %s\n' "$backup"

# Git archives contain imports/.gitkeep; preserve the server's real import tree.
chown james:james "$archive"
umask 022
runuser -u james -- tar -xzf "$archive" --no-same-owner \
    --exclude='imports' --exclude='imports/*'
umask 077
docker compose config --quiet
docker compose build --quiet app
COMPOSE_PROGRESS=quiet timeout 240 docker compose up -d --no-deps --wait app
docker compose exec -T app alembic current | grep -q '(head)'
[[ $(docker inspect --format '{{.State.Health.Status}}' photohearth-app-1) == healthy ]]
[[ $(docker inspect --format '{{.State.StartedAt}}' photohearth-db-1) == "$db_started" ]]
[[ $(docker inspect --format '{{.State.StartedAt}}' photohearth-gateway-1) == "$gateway_started" ]]
[[ $(curl --insecure --silent --show-error --output /dev/null --write-out '%{http_code}' https://192.168.1.140/api/health) == 200 ]]
[[ $(curl --insecure --silent --show-error --output /dev/null --write-out '%{http_code}' https://192.168.1.140/api/albums) == 401 ]]
printf '%s\n' "$revision" > data/deployment/deployed-sha
printf 'Desplegado y verificado: %s\n' "$revision"
