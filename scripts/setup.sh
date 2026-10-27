#!/bin/bash
# One-time setup on a Mac: Python venv with spotipy, workspace folders, and the
# Spotify app settings file. Safe to re-run.
#
#   bash setup.sh [CLIENT_ID]
#
# Everything goes in ~/.spotify-helper (venv, env file, login tokens) and
# ~/spotify-helper (your export and outputs). Nothing is installed system-wide.
set -euo pipefail

H="$HOME/.spotify-helper"
W="$HOME/spotify-helper"
mkdir -p "$W"/{export,data,genres,mood,audit,playlists}
mkdir -p "$H" && chmod 700 "$H"

PY=$(command -v python3 || true)
if [ -z "$PY" ] || ! "$PY" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
  echo "Python 3.9+ is needed. On a Mac run: xcode-select --install   (then re-run this script)"
  exit 1
fi

if [ ! -x "$H/venv/bin/python" ]; then
  "$PY" -m venv "$H/venv"
fi
"$H/venv/bin/pip" install --quiet --disable-pip-version-check spotipy==2.26.0
echo "spotipy installed in $H/venv"

if [ -n "${1:-}" ]; then
  if ! [[ "$1" =~ ^[0-9a-fA-F]{32}$ ]]; then
    echo "That doesn't look like a client ID (32 letters and numbers from the app's Settings page)."
    exit 1
  fi
  cat > "$H/env" <<EOF
export SPOTIPY_CLIENT_ID=$1
export SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
EOF
  chmod 600 "$H/env"
  echo "Saved client ID to $H/env"
fi
echo "Workspace: $W"
