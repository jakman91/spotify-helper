#!/usr/bin/env python3
"""Remove songs from Liked Songs, using a review CSV from the audit.

Only rows with remove=yes are touched. Without --apply it prints what it
would do and stops. With --apply it removes in batches of 40, then checks
each batch is gone and logs every URI to removed_log.csv, so anything can
be re-added later.

Uses the library-write token, separate from the read-only audit token.

    source ~/.spotify-helper/env
    ~/.spotify-helper/venv/bin/python remove_saved.py audit/remove_review.csv [--apply]
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone

from spotify_client import client

BATCH = 40


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("review_csv")
    ap.add_argument("--apply", action="store_true", help="actually remove (default is a dry run)")
    a = ap.parse_args()

    rows = [r for r in csv.DictReader(open(a.review_csv)) if r["remove"].strip().lower() == "yes"]
    kept = sum(1 for _ in csv.DictReader(open(a.review_csv))) - len(rows)
    print(f"{len(rows)} marked yes, {kept} kept")
    if not a.apply:
        for r in rows[:10]:
            print(f"  would remove: {r['name']} - {r['artist']}")
        print("Dry run only. Re-run with --apply to remove.")
        return

    sp = client("library-write")
    log_path = os.path.join(os.path.dirname(os.path.abspath(a.review_csv)), "removed_log.csv")
    new_log = not os.path.exists(log_path)
    removed, still_there = 0, []
    with open(log_path, "a", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["removed_at", "uri", "name", "artist", "album"])
        for i in range(0, len(rows), BATCH):
            batch = rows[i:i + BATCH]
            uris = [r["uri"] for r in batch]
            sp.current_user_saved_tracks_delete(uris)
            gone = sp.current_user_saved_tracks_contains(uris)
            now = datetime.now(timezone.utc).isoformat()
            for r, saved in zip(batch, gone):
                if saved:
                    still_there.append(r)
                else:
                    removed += 1
                    w.writerow([now, r["uri"], r["name"], r["artist"], r["album"]])
            print(f"  batch {i // BATCH + 1}: {len(batch)} sent", file=sys.stderr)

    print(f"Removed {removed}. Still saved after removal: {len(still_there)}")
    for r in still_there:
        print(f"  still saved: {r['name']} - {r['artist']} ({r['uri']})")
    print(f"Log: {log_path}")


if __name__ == "__main__":
    main()
