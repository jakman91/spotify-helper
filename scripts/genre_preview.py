#!/usr/bin/env python3
"""Preview genre playlists from tagged songs and a small playlist config.

    python3 genre_preview.py tracks_all.json genres/track_genres.json playlists/genre_playlists.json playlists/genre_preview.csv

genre_playlists.json is a list of playlists. Every key but name is optional:

    [
      {"name": "Indie rock", "genres": ["Indie rock"]},
      {"name": "EDM: 2012-2016", "genres": ["EDM"], "peak_year_max": 2016},
      {"name": "EDM: now", "genres": ["EDM"], "peak_year_min": 2017},
      {"name": "Taylor Swift", "artists": ["Taylor Swift"], "size": null}
    ]

genres / artists      a song matches if it is in any listed genre or by any listed artist
exclude_artists       drop these artists
peak_year_min / _max  the year the song was played most
min_plays             default 10 (the loved threshold)
size                  default 100, null keeps every match

Songs are ranked by plays. Output columns: playlist, rank, track, artist, plays, peak_year, uri.
"""

import csv
import json
import sys
from collections import Counter


def matches(t, genre, p):
    if t["plays"] < p.get("min_plays", 10):
        return False
    if p.get("genres") or p.get("artists"):
        if genre not in p.get("genres", []) and t["artist"] not in p.get("artists", []):
            return False
    if t["artist"] in p.get("exclude_artists", []):
        return False
    if "peak_year_min" in p and (t["peak_year"] or 0) < p["peak_year_min"]:
        return False
    if "peak_year_max" in p and (t["peak_year"] or 9999) > p["peak_year_max"]:
        return False
    return True


def main():
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    history, genres_path, config_path, out = sys.argv[1:]
    tracks = sorted(json.load(open(history)), key=lambda t: -t["plays"])
    genres = {k: (v.get("genre") if isinstance(v, dict) else v) for k, v in json.load(open(genres_path)).items()}
    config = json.load(open(config_path))
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["playlist", "rank", "track", "artist", "plays", "peak_year", "uri"])
        for p in config:
            pick = [t for t in tracks if matches(t, genres.get(t["id"], "Unsorted"), p)]
            total = len(pick)
            size = p.get("size", 100)
            if size is not None:
                pick = pick[:size]
            for i, t in enumerate(pick, 1):
                w.writerow([p["name"], i, t["track"], t["artist"], t["plays"], t["peak_year"], t["id"]])
            top = ", ".join(x for x, _ in Counter(t["artist"] for t in pick).most_common(4))
            print(f"{p['name']:32s} {total:5d} matched  {len(pick):4d} picked  top: {top}")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
