#!/usr/bin/env python3
"""Add songs to Liked Songs from the audit's loved_not_saved.csv.

Without --apply it prints what it would do and stops. With --apply it skips
anything already saved, adds the rest in batches of 40 (least-played first,
so your most-played songs end up at the top of Liked Songs), checks each
batch landed, and logs every URI to added_log.csv so it can be undone.

    source ~/.spotify-helper/env
    ~/.spotify-helper/venv/bin/python add_saved.py audit/loved_not_saved.csv [--min-plays 10] [--apply]
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone

from remove_saved import BATCH
from spotify_client import client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("loved_csv")
    ap.add_argument("--min-plays", type=int, default=10)
    ap.add_argument("--apply", action="store_true", help="actually add (default is a dry run)")
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(open(a.loved_csv)) if int(r["plays"]) >= a.min_plays]
    rows.sort(key=lambda r: int(r["plays"]))
    print(f"{len(rows)} songs at {a.min_plays}+ plays not in Liked Songs at audit time")
    if not a.apply:
        for r in rows[-10:][::-1]:
            print(f"  would add: {r['track']} - {r['artist']} ({r['plays']} plays)")
        print("Dry run only. Re-run with --apply to add.")
        return

    sp = client("library-write")
    log_path = os.path.join(os.path.dirname(os.path.abspath(a.loved_csv)), "added_log.csv")
    new_log = not os.path.exists(log_path)
    added, skipped, failed = 0, 0, []
    with open(log_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["added_at", "uri", "track", "artist", "plays"])
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            already = sp.current_user_saved_tracks_contains([r["id"] for r in batch])
            todo = [r for r, s in zip(batch, already) if not s]
            skipped += len(batch) - len(todo)
            if todo:
                sp.current_user_saved_tracks_add([r["id"] for r in todo])
                landed = sp.current_user_saved_tracks_contains([r["id"] for r in todo])
                now = datetime.now(timezone.utc).isoformat()
                for r, ok in zip(todo, landed):
                    if ok:
                        added += 1
                        w.writerow([now, r["id"], r["track"], r["artist"], r["plays"]])
                    else:
                        failed.append(r)
                f.flush()
            if (i // BATCH) % 10 == 0:
                print(f"  {i + len(batch)}/{len(rows)}", file=sys.stderr)

    print(f"Added {added}. Already saved: {skipped}. Did not save: {len(failed)}")
    for r in failed[:50]:
        print(f"  not saved: {r['track']} - {r['artist']} ({r['id']})")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
