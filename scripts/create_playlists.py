#!/usr/bin/env python3
"""Create playlists from a preview CSV (genre_preview.py or match_picks.py output).

The CSV needs playlist, rank and uri columns. Each playlist is created private
with its songs in rank order. Without --apply it prints the plan and stops.
Created playlists are logged to created_playlists.csv next to the CSV, and a
rerun skips names already in the log, so an interrupted run can simply be
started again.

    source ~/.spotify-helper/env
    ~/.spotify-helper/venv/bin/python create_playlists.py playlists/genre_preview.csv [--apply] [--only NAME ...]
"""

import argparse
import csv
import os
from collections import defaultdict
from datetime import datetime, timezone

from spotify_client import client

DESCRIPTION = "{name}. Built from my listening history."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preview_csv")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--description", default=DESCRIPTION,
                    help="playlist description; {name} is replaced with the playlist name")
    ap.add_argument("--only", nargs="+", help="create just these playlists from the CSV")
    a = ap.parse_args()

    lists = defaultdict(list)
    for r in csv.DictReader(open(a.preview_csv)):
        if not a.only or r["playlist"] in a.only:
            lists[r["playlist"]].append((int(r["rank"]), r["uri"]))
    log_path = os.path.join(os.path.dirname(os.path.abspath(a.preview_csv)), "created_playlists.csv")
    done = {r["name"] for r in csv.DictReader(open(log_path))} if os.path.exists(log_path) else set()

    todo = [n for n in sorted(lists) if n not in done]
    print(f"{len(todo)} playlists to create ({len(done)} already created)")
    for n in todo:
        print(f"  {n}: {len(lists[n])} songs")
    if not a.apply:
        print("Dry run only. Re-run with --apply.")
        return

    sp = client("playlist-write")
    new_log = not os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["created_at", "name", "id", "songs"])
        for n in todo:
            uris = [u for _, u in sorted(lists[n])]
            p = sp.current_user_playlist_create(n, public=False, description=a.description.format(name=n))
            for i in range(0, len(uris), 100):
                sp.playlist_add_items(p["id"], uris[i:i + 100])
            w.writerow([datetime.now(timezone.utc).isoformat(), n, p["id"], len(uris)])
            f.flush()
            print(f"  created {n} ({len(uris)} songs)")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
