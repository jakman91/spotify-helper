#!/usr/bin/env python3
"""Short list of loved songs for hand-picking a vibe playlist.

    python3 candidates.py tracks_all.json [--genres genres/track_genres.json] [--moods mood/track_moods.json]
                          [--genre NAME ...] [--mood Calm ...] [--artist NAME ...] [--min-plays 10] [--limit 400]

Filters are OR within a flag and AND across flags. Prints one line per song,
most played first: title | artist | plays | peak year | genre | moods | energy valence.
"""

import argparse
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("history")
    ap.add_argument("--genres")
    ap.add_argument("--moods")
    ap.add_argument("--genre", nargs="+")
    ap.add_argument("--mood", nargs="+")
    ap.add_argument("--artist", nargs="+")
    ap.add_argument("--min-plays", type=int, default=10)
    ap.add_argument("--limit", type=int, default=400)
    a = ap.parse_args()

    tracks = sorted(json.load(open(a.history)), key=lambda t: -t["plays"])
    genres = {k: v.get("genre") for k, v in json.load(open(a.genres)).items()} if a.genres else {}
    moods = json.load(open(a.moods))["tracks"] if a.moods else {}
    n = 0
    for t in tracks:
        if t["plays"] < a.min_plays:
            break
        g, m = genres.get(t["id"], ""), moods.get(t["id"], {})
        if a.genre and g not in a.genre:
            continue
        if a.mood and not set(a.mood) & set(m.get("moods", [])):
            continue
        if a.artist and t["artist"] not in a.artist:
            continue
        feats = f"e{m['ene']:.2f} v{m['val']:.2f}" if m else ""
        print(" | ".join([t["track"], t["artist"], str(t["plays"]), str(t["peak_year"]), g,
                          ",".join(m.get("moods", [])), feats]))
        n += 1
        if n >= a.limit:
            break


if __name__ == "__main__":
    main()
