#!/usr/bin/env bash
# Restore a backup made by deploy/backup.sh into the production stack.
# REPLACES the current database and every stored object.
#
#   deploy/restore.sh --file backups/voraxis-backup.tar   # a local .tar (e.g. copied from your PC)
#   deploy/restore.sh --slot a                            # download voraxis-a.tar from Blob
#
# The stack must have been started once (volumes created); the web, API and
# worker are stopped during the restore and started again at the end.
set -euo pipefail

cd "$(dirname "$0")/.."
compose_file=docker-compose.prod.yml
file=""
slot=""
while [ $# -gt 0 ]; do
  case "$1" in
    --file) file="$2"; shift 2 ;;
    --slot) slot="$2"; shift 2 ;;
    --compose) compose_file="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
[ -n "$file" ] || [ -n "$slot" ] || { echo "pass --file <tar> or --slot a|b" >&2; exit 2; }

compose() { docker compose -f "$compose_file" "$@"; }
log() { echo "[$(date -u +%FT%TZ)] $*"; }
# A host folder as `docker run -v` needs it (Git Bash on Windows uses C:/... paths).
host_path() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }
export MSYS_NO_PATHCONV=1

work=$(cd "$(dirname "${file:-.}")" && pwd)/.restore-$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

if [ -n "$slot" ]; then
  sas=$(grep -E '^BACKUP_SAS_URL=' .env | cut -d= -f2- || true)
  [ -n "$sas" ] || { echo "BACKUP_SAS_URL is empty in .env" >&2; exit 1; }
  file="$work/voraxis-$slot.tar"
  log "downloading voraxis-$slot.tar"
  curl --fail --silent --show-error -H "x-ms-version: 2021-08-06" \
    -o "$file" "${sas%%\?*}/voraxis-$slot.tar?${sas#*\?}"
fi
tar xf - -C "$work" db.dump objects.tgz < "$file"

log "stopping the web, API and worker"
compose stop web backend worker

log "restoring the database"
compose up -d database
until compose exec -T database sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do sleep 2; done
compose exec -T database sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner' < "$work/db.dump" \
  || log "pg_restore reported warnings (usually objects that did not exist yet); check the app afterwards"

log "restoring the object store"
compose up -d minio
minio=$(compose ps -q minio)
docker run --rm --volumes-from "$minio" -v "$(host_path "$work")":/in:ro debian:bookworm-slim \
  sh -c "find /data -mindepth 1 -delete && tar --xattrs --xattrs-include='user.*' -xzf /in/objects.tgz -C /data"
compose restart minio

log "starting everything"
compose up -d
log "done"
