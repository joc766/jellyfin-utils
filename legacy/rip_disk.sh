#!/usr/bin/env bash

: ${RAW_MOVIES_BASE:="/Volumes/Sandisk/Raw Movies"}

MESSAGES_PATH="$RAW_MOVIES_BASE/messages.txt"

makemkvcon info -r disc:9999 --messages="$MESSAGES_PATH"

IFS=, read -r raw_drive_name _ _ _ _ disc_name _ < <(grep -m1 '^DRV:' "$MESSAGES_PATH")

drive_name="disc:${raw_drive_name##*:}"

if [[ -z $disc_name ]]; then
  echo "Error: Disc name is empty" >&2
  exit 1
fi

OUTPUT="$RAW_MOVIES_BASE/${disc_name//\"/}"

mkdir -p "$OUTPUT"

makemkvcon mkv -r --cache=1024 "$drive_name" all "$OUTPUT" --messages="$OUTPUT/log.txt" --progress=-same

printf 'MAKEMKV_FOLDER_NAME=%q\n' "$(echo "$disc_name" | tr -d '"')"

exit 0
