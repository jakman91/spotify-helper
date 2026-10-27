#!/usr/bin/env python3
"""Tag songs with a genre by tagging their artists. No Spotify API needed.

Spotify no longer returns genres to new developer apps, so Claude tags each
artist into one of the person's own genre buckets, and every song by that
artist inherits it.

    python3 genres.py todo  tracks_all.json genres/artist_genres.json genres/artists_to_tag.csv [--min-plays 10]
    python3 genres.py apply tracks_all.json genres/artist_genres.json genres/track_genres.json

todo   lists artists with at least one loved song that are not tagged yet,
       most loved songs first, with their top 3 songs for context.
apply  writes {track_uri: {"genre": name}} for every song (untagged artists
       get "Unsorted") and prints song counts per genre.

artist_genres.json is a flat {"Artist name": "Genre"} object.
"""

import argparse
import csv
import json
import os
from collections import Counter, defaultdict


def load_tags(path):
    return json.load(open(path)) if os.path.exists(path) else {}


def todo(a):
    tracks = json.load(open(a.history))
    tags = load_tags(a.tags)
    loved = defaultdict(list)
    for t in tracks:
        if t["plays"] >= a.min_plays and t["artist"] not in tags:
            loved[t["artist"]].append(t)
    rows = sorted(loved.items(), key=lambda kv: (-len(kv[1]), -sum(t["plays"] for t in kv[1])))
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["artist", "loved_songs", "plays", "top_songs"])
        for artist, ts in rows:
            ts.sort(key=lambda t: -t["plays"])
            w.writerow([artist, len(ts), sum(t["plays"] for t in ts), " | ".join(t["track"] for t in ts[:3])])
    print(f"{len(tags)} artists already tagged, {len(rows)} to tag -> {a.out}")


def apply(a):
    tracks = json.load(open(a.history))
    tags = load_tags(a.tags)
    out = {t["id"]: {"genre": tags.get(t["artist"], "Unsorted")} for t in tracks}
    json.dump(out, open(a.out, "w"))
    loved = [t for t in tracks if t["plays"] >= a.min_plays]
    by_genre = Counter(tags.get(t["artist"], "Unsorted") for t in loved)
    print(f"Loved songs ({a.min_plays}+ plays) per genre:")
    for g, n in by_genre.most_common():
        print(f"  {n:5d}  {g}")
    left = Counter(t["artist"] for t in loved if t["artist"] not in tags)
    if left:
        print("Top untagged artists: " + ", ".join(f"{x} ({n})" for x, n in left.most_common(10)))
    print(f"Wrote {len(out)} songs -> {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["todo", "apply"])
    ap.add_argument("history", help="tracks_all.json from build_datasets.py")
    ap.add_argument("tags", help="artist_genres.json")
    ap.add_argument("out")
    ap.add_argument("--min-plays", type=int, default=10)
    a = ap.parse_args()
    (todo if a.cmd == "todo" else apply)(a)


if __name__ == "__main__":
    main()
