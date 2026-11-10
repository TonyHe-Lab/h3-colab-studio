#!/usr/bin/env bash
# Stitch H3 shot clips into one video, in filename order.
# Usage: stitch.sh OUTPUT.mp4 SHOT1.mp4 SHOT2.mp4 [SHOT3.mp4 ...]
# All clips must share codec, resolution and fps (they do when generated
# with the same workflow settings). Re-encodes to normalize parameters.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Usage: stitch.sh OUTPUT.mp4 SHOT1.mp4 SHOT2.mp4 [SHOT...]" >&2
  exit 1
fi

OUT="$1"; shift
LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT

resolve_path() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  else
    python3 -c 'import os, sys; print(os.path.abspath(sys.argv[1]))' "$1"
  fi
}

for f in "$@"; do
  abs_path="$(resolve_path "$f")"
  escaped_path="$(printf "%s" "$abs_path" | sed "s/'/'\\\\''/g")"
  printf "file '%s'\n" "$escaped_path" >> "$LIST"
done

ffmpeg -y -v error -f concat -safe 0 -i "$LIST" \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 128k "$OUT"

ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate \
  -show_entries format=duration,size -of default=noprint_wrappers=1 "$OUT"
