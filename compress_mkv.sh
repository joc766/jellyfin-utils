#!/bin/bash
#
# Perform lossless H264 compression on a ripped MKV file
# Arguments:
#   $1: An absolute path describing the location of the original MKV file.
#   Must be named "*_original.mkv"
# Options:
#   -d: flag for 480p DVD files
#   -w: flag for widescreen resolutions. Requires -d flag to have an effect

err() {
  echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2
}

usage() {
  echo "Usage: $0 [-d] [-w] <src>"
  exit 1
}

set -euo pipefail

while getopts 'dw' opt; do
  case "${opt}" in
  d) DVD='true' ;;
  w) SCALE='854:480' ;;
  # -o) OUTPUT=$2 ;;
  --) break ;;
  \?) err "Unknown option: $opt" ;;
  *) break ;;
  esac
done

shift $((OPTIND - 1))

if [[ ! $# -eq 1 ]]; then
  err "Expected 1 positional arg. Got $#"
  echo "$@"
  usage
fi

INPUT="$1"
INPUT_BASENAME="$(basename "$INPUT")"
INPUT_DIRNAME="$(dirname "$INPUT")"

if [[ $INPUT_DIRNAME != "/"* ]]; then
  err "Input must be an absolute path"
  exit 1
fi

if [[ ! -f $INPUT || ! $INPUT_BASENAME =~ _original\.[[:alpha:]]+$ ]]; then
  err "File name must end with _original.*"
  exit 1
fi

INPUT_SUFFIX="${INPUT_BASENAME##*.}"
OUTPUT="${INPUT_DIRNAME}/${INPUT_BASENAME%_original.*}.mp4"

DEFAULT_DVD_FILTERS=(-vf "scale=${SCALE:="trunc(480*dar/2)*2:480"}:flags=lanczos,setsar=1,setfield=prog")
DEFAULT_DVD_FORMAT_FLAGS=(-fflags +genpts -avoid_negative_ts make_zero)

ff_args=(
  -i "$INPUT"
  -map_metadata 0 -map_chapters 0
  -map 0:v:0 -map 0:a:0 -map -sn
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p
  -x264-params interlaced=0
  -c:a libfdk_aac -ac 2 -ab 256k
  -c:s copy
  -movflags +faststart
)

if [[ -n "${DVD:-}" ]]; then
  ff_args+=("${DEFAULT_DVD_FILTERS[@]}")
  ff_args+=("${DEFAULT_DVD_FORMAT_FLAGS[@]}")
fi

ffmpeg "${ff_args[@]}" "$OUTPUT"
