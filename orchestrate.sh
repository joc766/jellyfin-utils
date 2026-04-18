#!/usr/bin/env bash

set -euo pipefail

RAW_MOVIES_BASE="/Volumes/SanDisk/Raw Movies"
COMPRESSED_MOVIES_BASE="/Volumes/SanDisk/Movies"

while getopts 'd' opt; do
  case "${opt}" in
  d) DVD="true" ;;
  --) break ;;
  \?) err "Unknown option: $opt" ;;
  *) break ;;
  esac
done

shift $((OPTIND - 1))

imdb_id="$1"

echo "Running makemkvcon to rip disk..."
eval "$(./rip_disk.sh)"

echo "Reorganizing files..."
eval "$(./organize_files.sh "$imdb_id" "$MAKEMKV_FOLDER_NAME")"

echo "Compressing MKV to H264 MP4 AAC Stereo..."
if [[ "$DVD" == "true" ]]; then
  eval "$(./compress_mkv.sh -d -o "$JELLYFIN_COMPRESSED_BASE" "$JELLYFIN_RAW_PATH")"
else
  eval "$(./compress_mkv.sh -o "$JELLYFIN_COMPRESSED_BASE" "$JELLYFIN_RAW_PATH")"
fi

echo "Syncing compressed content to server..."
eval "$(./sync-movie-to-server.sh "$JELLYFIN_COMPRESSED_BASE")"

exit 0
