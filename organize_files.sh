#!/usr/bin/env bash
#
# Script to reorganize files after [[rip_disk]] has pulled out relevant
# information from the disc and before [[compress_mkv]] has begun the
# compression process.
#
# Final state: a folder exists in both "/Volumes/SanDisk/Raw Movies" and
# "/Volumes/SanDisk/movies" with a name starting with the official title of the
# movie, followed by its year in parentheses and ending with
# "[imdbid-{imdbid}]". Additionally, the
# "/Volumes/SanDisk/Raw Movies/{name} ({year}) [imdbid-{imdbid}]" folder
# contains a file that uses an identical naming convention in addition to the
# suffix "_original.mkv"
#
# The MKV file that is renamed as described at the end of the previous paragraph
# will be the largest file that exists in $2 at the time the program is executed.
#
# Parameters:
#   - $1: the IMDB ID of the film
#   - $2: the name of the folder created by [[rip_disk]] (makemkvcon)
#

set -euo pipefail

: ${RAW_MOVIES_BASE:="/Volumes/SanDisk/Raw Movies"}
: ${COMPRESSED_MOVIES_BASE:="/Volumes/SanDisk/movies"}

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

usage() {
  echo "Usage: $0 <imdb_id> <makemkv_folder_name>"
  exit 1
}

if [[ $# -ne 2 ]]; then
  err "Missing arguments."
  usage
fi

imdb_id="$1"
OMDB_API_BASE_URL="https://omdbapi.com"
OMDB_API_KEY="$(security find-generic-password -a "$USER" -s "OMDB_API" -w)"

if [[ $? -ne 0 ]]; then
  err "OMDB_API_KEY service password does not exist in system keychain."
  exit 1
fi

if [[ ! "$imdb_id" =~ ^tt[0-9]+$ ]]; then
  err "imdb_id Provided ($imdb_id) is not a valid IMDB ID (ex: tt3896198)."
  usage
fi

makemkv_folder_name="$2"
makemkv_path="$RAW_MOVIES_BASE/$makemkv_folder_name"

if [[ ! -d "$makemkv_path" ]]; then
  err "MakeMKV path provided ($makemkv_path) not found or is not a directory."
  usage
fi

response="$(curl -sS "$OMDB_API_BASE_URL/?i=$imdb_id&apikey=$OMDB_API_KEY")"

if [[ "$(echo "$response" | jq -r '.Response')" == "False" ]]; then
  err "$(echo "$response" | jq '.Error')"
  exit 1
fi

omdb_name="$(echo "$response" | jq -r '.Title' | tr ":" "-")"
omdb_year="$(echo "$response" | jq -r '.Year')"
jellyfin_name="$omdb_name ($omdb_year) [imdbid-$imdb_id]"

largest_file="$(ls -S "$makemkv_path" | head -n 1)"
raw_movie_path="$RAW_MOVIES_BASE/$jellyfin_name"

# Perform actual renames and mkdirs

jellyfin_raw_path="$raw_movie_path/${jellyfin_name}_original.mkv"
jellyfin_compressed_base="$COMPRESSED_MOVIES_BASE/$jellyfin_name"

mv "$makemkv_path" "$raw_movie_path"
mv "$raw_movie_path/$largest_file" "$jellyfin_raw_path"
mkdir "$jellyfin_compressed_base"

printf 'JELLYFIN_RAW_PATH=%q\n' "$jellyfin_raw_path"
printf 'JELLYFIN_COMPRESSED_BASE=%q\n' "$jellyfin_compressed_base"

exit 0
