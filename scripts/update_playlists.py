#!/usr/bin/env python3
"""Rename existing playlists and replace their songs from a preview CSV.

Takes pairs of OLD=NEW names. OLD is looked up in created_playlists.csv
next to the preview; NEW is the playlist name in the preview. Without
--apply it prints the plan. With --apply it saves the old song list to
updated_log.csv (so it can be put back), renames, replaces the songs in
rank order, and updates created_playlists.csv to the new name.

Use the same name on both sides to keep the name and only replace the songs.

    source ~/.spotify-helper/env
    ~/.spotify-helper/venv/bin/python update_playlists.py playlists/genre_preview.csv \
        "EDM: old=EDM: 2012-2016" "Indie=Indie" [--apply]
"""

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from spotify_client import client, page_all
from create_playlists import DESCRIPTION


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preview_csv")
    ap.add_argument("pairs", nargs="+", help='"OLD NAME=NEW NAME"')
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    out_dir = os.path.dirname(os.path.abspath(a.preview_csv))
    created_path = os.path.join(out_dir, "created_playlists.csv")
    created = list(csv.DictReader(open(created_path)))
    ids = {r["name"]: r["id"] for r in created}
    lists = defaultdict(list)
    for r in csv.DictReader(open(a.preview_csv)):
        lists[r["playlist"]].append((int(r["rank"]), r["uri"]))

    plan = []
    for pair in a.pairs:
        old, new = pair.split("=", 1)
        if old not in ids:
            raise SystemExit(f"{old!r} not found in {created_path}")
        if new not in lists:
            raise SystemExit(f"{new!r} not found in {a.preview_csv}")
        plan.append((old, new, ids[old], [u for _, u in sorted(lists[new])]))
    for old, new, pid, uris in plan:
        print(f"  {old}  ->  {new}  ({len(uris)} songs, playlist {pid})")
    if not a.apply:
        print("Dry run only. Re-run with --apply.")
        return

    sp = client("playlist-write")
    log_path = os.path.join(out_dir, "updated_log.csv")
    new_log = not os.path.exists(log_path)
    with open(log_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["updated_at", "id", "old_name", "new_name", "old_uris"])
        for old, new, pid, uris in plan:
            before = [(it.get("track") or it.get("item") or {}).get("uri")
                      for it in page_all(sp, sp.playlist_items(pid, limit=100, additional_types=("track",)))]
            w.writerow([datetime.now(timezone.utc).isoformat(), pid, old, new, json.dumps([u for u in before if u])])
            f.flush()
            sp.playlist_change_details(pid, name=new, description=DESCRIPTION.format(name=new))
            sp.playlist_replace_items(pid, uris[:100])
            for i in range(100, len(uris), 100):
                sp.playlist_add_items(pid, uris[i:i + 100])
            for r in created:
                if r["id"] == pid:
                    r["name"] = new
            print(f"  updated {old} -> {new} ({len(uris)} songs)")
    with open(created_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(created[0]))
        w.writeheader()
        w.writerows(created)
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
