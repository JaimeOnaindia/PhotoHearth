# PhotoHearth production reference

This reference contains connection metadata and procedures, not credentials.
Treat all live state as dynamic and verify it before acting.

## Topology

- Production host: `192.168.1.140`, SSH user `james`.
- Production directory: `/home/james/photohearth`.
- Application: `https://192.168.1.140` on the private LAN.
- Jenkins: `https://192.168.1.140:8443` on the private LAN.
- `compose.yaml` owns `app`, PostgreSQL `db`, and Caddy `gateway`.
- `compose.ci.yaml` adds `jenkins`, `ci-agent`, and the disposable `ci-db`.
- Production PostgreSQL and photo storage use named volumes. The import directory
  is mounted read-only into the application.
- `PhotoHearth` validates and packages code. The separate `PhotoHearth Deploy`
  job deploys only when started manually.

Do not publish these services on the Internet. Remote access requires a separate
private VPN design.

## Local access without exposing credentials

The ignored local files under `data/deployment/` may include an SSH identity,
Jenkins access material, verification helpers, and private backups. Check their
existence and permissions, but never display their contents.

Use SSH like this; OpenSSH reads the private key itself:

```bash
ssh -i data/deployment/xiaomi_ed25519 james@192.168.1.140
```

The public certificate `photohearth-ca.crt` is not a secret. Private SSH keys,
password files, `.env`, PostgreSQL secrets, and backup archives are secrets.

Use the existing helpers without inspecting their embedded/local configuration:

```bash
.venv/bin/python data/deployment/verify.py
.venv/bin/python data/deployment/jenkins_job.py status
.venv/bin/python data/deployment/jenkins_job.py log
.venv/bin/python data/deployment/jenkins_job.py verify
```

Consult the helper's safe `--help` output if an interface has changed. Do not
invent or echo credentials when a helper reports that local configuration is
missing.

## CI gate

Before release:

1. Confirm the worktree and intended commit with `git status --short` and
   `git rev-parse HEAD`.
2. Run the relevant local checks from `package.json`, `pyproject.toml`, and the
   repository workflow.
3. Push the exact commit requested by the user.
4. Start or await the `PhotoHearth` Jenkins job.
5. Require success for that exact Git SHA, not merely the latest green build.
6. Confirm the source artifact exists and corresponds to the same SHA.

Jenkins runs Ruff, TypeScript, ESLint, pytest against SQLite and PostgreSQL,
the production web build, and Playwright desktop/mobile flows. Re-read
`Jenkinsfile` before relying on this list.

For a routine release, the manual `PhotoHearth Deploy` job triggers CI, copies
that build's artifact and SHA, then uses a restricted SSH key to run the fixed
server command. Its `DRY_RUN` parameter verifies access and package handling
without changing production. See `deploy/JENKINS.md` for setup and key rotation.

## Release preparation

Build a source archive from the verified commit rather than copying the dirty
working tree:

```bash
git archive --format=tar.gz --output=/tmp/photohearth-release.tar.gz HEAD
```

Inspect the archive before transfer. It must not contain `.env`, `.git`, `data/`,
private backups, keys, or generated dependency/build directories. Record a SHA-256
locally and verify the same digest after transfer.

Extract the archive over `/home/james/photohearth` only after confirming that the
server-only `.env`, `data/`, `imports/`, and named volumes will remain untouched.
Run `docker compose config --quiet` before building.

## Application-only deployment

Capture the current container state first. From the production directory, use:

```bash
sudo docker compose build app
sudo docker compose up -d --no-deps --wait app
```

`--no-deps` is intentional: a normal code release must not recreate PostgreSQL
or Caddy. Do not use `docker compose down`, and never use `down -v`.

If the change modifies Compose, database/storage layout, secrets, networking,
Jenkins, or the gateway, stop and plan that as a separate infrastructure phase.
Follow the matching deployment guide and obtain explicit approval.

## Backups and migrations

Before a schema, storage, import, restore, or risky production change, create and
verify a PhotoHearth application backup using `deploy/DEBIAN.md`. Store a copy on
another encrypted device when the data matters; a second file on the same SSD is
not disaster recovery.

Use Alembic only through the application's established startup/management flow.
Inspect the current and target revision before deployment. Follow
`deploy/POSTGRES.md` for migration or restore work. Restore into a new empty
database and new storage directory; never overwrite an active library.

## Post-deployment verification

Verify all applicable items:

- `docker compose ps` reports a healthy `app` and healthy `db`.
- The public health endpoint succeeds over HTTPS.
- An unauthenticated private API request is rejected.
- Login succeeds through the normal application flow without printing cookies.
- Alembic reports the expected revision.
- The changed user flow works, including desktop/mobile when relevant.
- PostgreSQL and Caddy start timestamps are unchanged after an app-only release.
- Logs contain no new migration, permission, storage, or repeated worker errors.
- The temporary release archive is removed after success.

On failure, preserve logs and the previous image/archive, avoid destructive
cleanup, and roll back only with a verified plan that accounts for schema
compatibility and any data written after deployment.
