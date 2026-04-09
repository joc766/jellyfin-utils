#!/bin/bash

MOVIE_ROOT="/Volumes/Sandisk/Raw Movies"

MESSAGES_PATH="$MOVIE_ROOT/messages.txt"

makemkvcon info -r disc:9999 --messages="$MESSAGES_PATH"

IFS=, read -r raw_drive_name _ _ _ _ disc_name _ < <(grep -m1 '^DRV:' "$MESSAGES_PATH")

drive_name="disc:${raw_drive_name##*:}"

if [[ ! -z $disc_name ]]; then
  echo $disc_name
else
  echo "Error: Disc name is empty" >&2
  exit 1
fi

OUTPUT="$MOVIE_ROOT/${disc_name//\"/}"

mkdir -p "$OUTPUT"

makemkvcon mkv -r --cache=1024 "$drive_name" all "$OUTPUT" --messages="$OUTPUT/log.txt" --progress=-same
