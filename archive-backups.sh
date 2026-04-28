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

# if [[ ! $INPUT =~ /$ ]]; then
#   echo "Input must end with a slash; this program is designed to copy only the contents of the Raw Movies directory" >&2
#   exit 1
# fi

REMOTE_DEST="jackoconnor@192.168.50.2:'/mnt/storage/raw-movies-backup/'"

rsync -rltDvh --delete --partial ${DRY_RUN_ARG:+$DRY_RUN_ARG} --append --progress --stats --exclude '.DS_Store' \
  -e "ssh -T -c aes128-gcm@openssh.com -o Compression=no -o ServerAliveInterval=30 -o ServerAliveCountMax=6" \
  --rsync-path='sudo -n rsync' \
  --chmod=Du=rwx,Dg=rx,Do=rx,Fu=rw,Fg=r,Fo=r \
  "$INPUT" \
  "$REMOTE_DEST"

exit 0
