#!/usr/bin/env bash

input="$1"
output="$2"

echo "$input"

while IFS= read -r -d '' file; do
  if [[ -f "$file" ]]; then
    ./compress_mkv.sh -d -o "$output" "$file"
  fi
done < <(find -E "$input" -type f -regex '.*\.mkv$' -print0)
