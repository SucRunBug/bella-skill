#!/usr/bin/env bash
# bella-ai-collage-maker environment self-check.
# Exit 0 = all good; exit 1 = at least one item missing (details on stdout).

set -u

FAIL=0

ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; FAIL=1; }

# ffmpeg / ffprobe normalize the auto-approved still and create the solid-color
# first frame for the final manual video package.
if command -v ffmpeg >/dev/null 2>&1 && command -v ffprobe >/dev/null 2>&1; then
  ok "ffmpeg / ffprobe 可用"
else
  bad "ffmpeg / ffprobe 缺失（macOS: brew install ffmpeg；Debian/Ubuntu: sudo apt install ffmpeg）"
fi

exit $FAIL
