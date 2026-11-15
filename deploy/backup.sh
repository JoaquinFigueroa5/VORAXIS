#!/usr/bin/env bash
# Back up Voraxis: database dump + every object in the S3 store, in one .tar.
#
#   deploy/backup.sh                         # production stack, upload to Blob
#   deploy/backup.sh --no-upload             # only write the .tar locally
#   deploy/backup.sh --compose docker-compose.yml --no-upload
#                                            # from the development stack (to seed a server)
#
# Upload: a single PUT to the Blob container in BACKUP_SAS_URL (.env). Two slots,
# voraxis-a.tar and voraxis-b.tar, alternate by day, so the last two days are kept
# and the total stays inside the 5 GB of free Blob storage.
# Daily on the server (crontab -e):
#   0 4 * * * /home/azureuser/VORAXIS/deploy/backup.sh >> /home/azureuser/backup.log 2>&1
set -euo pipefail

cd "$(dirname "$0")/.."
compose_file=docker-compose.prod.yml
upload=1
out_dir=backups
while [ $# -gt 0 ]; do
  case "$1" in
    --compose) compose_file="$2"; shift 2 ;;
    --no-upload) upload=0; shift ;;
    --out) out_dir="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

compose() { docker compose -f "$compose_file" "$@"; }
log() { echo "[$(date -u +%FT%TZ)] $*"; }
# A host folder as `docker run -v` needs it (Git Bash on Windows uses C:/... paths).
host_path() { if command -v cygpath >/dev/null 2>&1; then cygpath -m "$1"; else echo "$1"; fi; }
export MSYS_NO_PATHCONV=1

mkdir -p "$out_dir"
work=$(cd "$out_dir" && pwd)/.work-$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

log "dumping the database"
compose exec -T database sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner' > "$work/db.dump"

log "archiving the object store"
minio=$(compose ps -q minio)
[ -n "$minio" ] || { echo "the minio service is not running" >&2; exit 1; }
# GNU tar with --xattrs: VersityGW keeps each object's etag, content type and the
# bucket's owner in extended attributes, and a plain tar would drop them.
docker run --rm --volumes-from "$minio":ro -v "$(host_path "$work")":/out debian:bookworm-slim \
  tar --xattrs --xattrs-include='user.*' -czf /out/objects.tgz -C /data .

archive="$out_dir/voraxis-backup.tar"
tar cf - -C "$work" db.dump objects.tgz > "$archive"
log "wrote $archive ($(du -h "$archive" | cut -f1))"

if [ "$upload" = 1 ]; then
  sas=$(grep -E '^BACKUP_SAS_URL=' .env | cut -d= -f2- || true)
  if [ -z "$sas" ]; then
    log "BACKUP_SAS_URL is empty in .env: kept the local copy only"
    exit 0
  fi
  slot=$([ $(( $(date -u +%s) / 86400 % 2 )) = 0 ] && echo a || echo b)
  url="${sas%%\?*}/voraxis-$slot.tar?${sas#*\?}"
  log "uploading to slot $slot"
  curl --fail --silent --show-error -X PUT \
    -H "x-ms-blob-type: BlockBlob" -H "x-ms-version: 2021-08-06" \
    --upload-file "$archive" "$url"
  log "uploaded voraxis-$slot.tar"
fi
