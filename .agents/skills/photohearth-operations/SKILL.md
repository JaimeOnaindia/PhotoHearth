---
name: photohearth-operations
description: Operate, verify, release, deploy, back up, and troubleshoot PhotoHearth on its private Xiaomi Docker Compose host. Use for SSH access, Jenkins CI, production releases, database migrations, backups, health checks, rollbacks, or questions about the deployed architecture in this repository.
---

# PhotoHearth operations

Use this skill only for operational work on PhotoHearth. Read
[`references/production.md`](references/production.md) before accessing Jenkins or
the production server.

## Protect secrets and user data

- Treat `data/deployment/` as an opaque, local-only credential and operations
  directory. It is ignored by Git.
- Never open, print, copy into a prompt, or commit passwords, private keys,
  `.env` files, database secrets, backups, or session data.
- Invoke the existing helper programs and SSH identity by path. The underlying
  tools consume the secrets; the model does not need their contents.
- Do not add a secret to this skill, documentation, shell history, a command-line
  argument, Jenkins output, or an artifact.
- Require current user authorization before mutating production, triggering a
  release, restoring a backup, or changing infrastructure.

## Follow the repository sources of truth

- Read `compose.yaml` for production services and `compose.ci.yaml` for Jenkins.
- Read `Jenkinsfile` before changing or describing CI behavior.
- Use `deploy/DEBIAN.md` for host operations, `deploy/JENKINS.md` for CI, and
  `deploy/POSTGRES.md` for database, backup, restore, and location privacy work.
- Query live state instead of recording transient facts such as the latest build,
  deployed commit, container ID, or uptime in this skill.

## Choose the smallest safe workflow

1. Inspect Git status and re-read every file that will change.
2. Run the configured checks that cover the change.
3. Keep application, operational, and infrastructure changes in separate phases.
4. Push the exact commit and require a successful Jenkins build for that SHA.
5. Back up production before schema, storage, migration, or risky release work.
6. For an application-only release, rebuild and recreate only `app`; do not
   restart PostgreSQL, Caddy, or Jenkins.
7. Verify health, authentication boundaries, migrations, and relevant user flows.
8. Remove temporary release archives from the server after verification.

## Keep verification output compact

- Run the full required coverage, but use quiet reporters by default: `pytest -q`
  and `npm test -- --reporter=dot`.
- Do not print complete successful logs. Report the command, pass/fail totals, and
  elapsed time only.
- When a check fails, show the focused failure and rerun only its target with a
  more detailed reporter before repeating the compact full suite.
- Query Jenkins with `status` or `verify`; read its full log only to diagnose a
  failure, and surface only the relevant excerpt.

Never run `docker compose down -v`. Never replace `.env`, `data/`, imports,
named volumes, or server-only secrets with files from a source archive.
