#!/usr/bin/env bash

set -euo pipefail

# Assume the user is passing a directory as argument to the program. Use only absolute paths

DRY_RUN_ARG=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN_ARG="--dry-run"
  INPUT="$2"
else
  INPUT="$1"
fi

if [ ! -d "$INPUT" ]; then
  echo "Input must be a directory that exists" >&2
  exit 1
fi

if [[ ! $INPUT =~ ^/ ]]; then
  echo "Input must be an absolute path" >&2
  exit 1
fi

if [[ $INPUT =~ /$ ]]; then
  echo "Input must not end with a slash; this program is designed to copy an entire directory, not just its contents" >&2
  exit 1
fi

REMOTE_DEST="jackoconnor@192.168.50.2:/mnt/storage/jellyfin/movies/"

# -r: recursive (copy subdirs), -t: preserve timestamps, -D: copy special file types, -v: verbose, -h: human readable sizes, -W: whole file method, faster
# --partial: do not delete partial uploads (for failure)
# --stats: show verbose stats at the end
# --progress: periodically report progress
rsync -rtvhW --delete --partial ${DRY_RUN_ARG:+$DRY_RUN_ARG} --progress --stats --exclude '.DS_Store' \
  -e "ssh -T -c aes128-gcm@openssh.com -o Compression=no -o ServerAliveInterval=30 -o ServerAliveCountMax=6" \
  --rsync-path='sudo -n rsync' \
  --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r \
  "$INPUT" \
  "$REMOTE_DEST"

exit 0
