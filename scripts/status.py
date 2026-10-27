#!/usr/bin/env python3
"""Show where someone is in the spotify-helper workflow.

    python3 status.py [workspace]   (default ~/spotify-helper)

Checks files only; never calls Spotify. Prints one line per step and the next step.
"""

import glob
import os
import sys

W = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/spotify-helper")
H = os.path.expanduser("~/.spotify-helper")


def has(*parts):
    return os.path.exists(os.path.join(W, *parts))


def env_ok():
    p = os.path.join(H, "env")
    return os.path.exists(p) and "SPOTIPY_CLIENT_ID=" in open(p).read()


STEPS = [
    ("Export in export/", lambda: bool(glob.glob(os.path.join(W, "export", "**", "Streaming_History_Audio_*.json"), recursive=True)),
     "spotify-start: request the Extended streaming history export and unzip it into export/"),
    ("Dashboard built", lambda: has("dashboard.html"), "spotify-dashboard"),
    ("Python + spotipy installed", lambda: os.path.exists(os.path.join(H, "venv", "bin", "python")),
     "spotify-start: run setup.sh"),
    ("Spotify app client ID saved", env_ok, "spotify-start: create the Spotify developer app"),
    ("Genres tagged", lambda: has("genres", "track_genres.json"), "spotify-enrich: genres"),
    ("Moods pulled", lambda: has("mood", "track_moods.json"), "spotify-enrich: moods"),
    ("Library audit", lambda: has("audit", "summary.md"), "spotify-library: audit"),
    ("Liked Songs cleanup", lambda: has("audit", "removed_log.csv") or has("audit", "added_log.csv"),
     "spotify-library: add loved songs / remove rarely played ones"),
    ("Playlists created", lambda: bool(glob.glob(os.path.join(W, "playlists", "created_playlists.csv"))),
     "spotify-library: genre and vibe playlists"),
]


def main():
    print(f"Workspace: {W}")
    nxt = None
    for name, check, hint in STEPS:
        ok = check()
        print(f"  [{'x' if ok else ' '}] {name}")
        if not ok and nxt is None:
            nxt = hint
    print(f"Next: {nxt}" if nxt else "All steps done.")


if __name__ == "__main__":
    main()
