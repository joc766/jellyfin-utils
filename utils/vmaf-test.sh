#!/usr/bin/env bash
set -euo pipefail

DIST="$1"
REF="$2"
OUT="${3:-vmaf.json}"

START=600 # 10 minutes
END=720   # 15 minutes

FPS="24000/1001"

ffmpeg \
  -i "$DIST" \
  -i "$REF" \
  -filter_complex "
    [0:v]
      trim=start=${START}:end=${END},
      setpts=PTS-STARTPTS,
      fps=${FPS},
      format=yuv420p
    [dist];

    [1:v]
      trim=start=${START}:end=${END},
      setpts=PTS-STARTPTS,
      fps=${FPS},
      format=yuv420p
    [ref];

    [dist][ref]
      libvmaf=log_fmt=json:log_path='${OUT}'
  " \
  -f null -
