#!/usr/bin/env python3
"""Pull ReccoBeats audio features for loved tracks (plays >= 10). Read-only, no Spotify API.

ReccoBeats (api.reccobeats.com) is free and needs no key. Tries each track's
main Spotify ID first, then its other_uris for misses.
Usage: python3 mood_pull.py tracks_all.csv out_dir [min_plays=10]
Writes out_dir/track_features.csv (+ cache.json so reruns skip known IDs).
"""
import csv, json, sys, time, urllib.request, urllib.error
from pathlib import Path

UA = "spotify-helper-mood-pull/0.1"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("mood")
OUT.mkdir(parents=True, exist_ok=True)
CACHE = OUT / "cache.json"
COLS = ["valence", "energy", "danceability", "tempo", "acousticness", "instrumentalness",
        "loudness", "speechiness", "liveness", "key", "mode"]


def get(url):
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", 5)) + 1)
                continue
            return {}
        except Exception:
            time.sleep(2 ** i)
    return {}


def fetch(ids, cache):
    todo = [i for i in ids if i not in cache]
    for n in range(0, len(todo), 40):
        batch = todo[n:n + 40]
        for it in get("https://api.reccobeats.com/v1/audio-features?ids=" + ",".join(batch)).get("content", []):
            key = (it.get("href") or "").rsplit("/", 1)[-1]
            if key in batch:
                cache[key] = it
        for b in batch:
            cache.setdefault(b, None)
        time.sleep(0.4)
        if n % 800 == 0:
            CACHE.write_text(json.dumps(cache))
            print(f"  {n + len(batch)}/{len(todo)}", flush=True)
    CACHE.write_text(json.dumps(cache))


def main():
    min_plays = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    rows = [r for r in csv.DictReader(open(sys.argv[1])) if int(r["plays"]) >= min_plays]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    sid = lambda u: u.rsplit(":", 1)[-1]

    fetch([sid(r["id"]) for r in rows], cache)
    main_hits = sum(1 for r in rows if cache.get(sid(r["id"])))
    alts = [sid(u) for r in rows if not cache.get(sid(r["id"])) for u in r["other_uris"].split("|") if u]
    print(f"main id hits {main_hits}/{len(rows)}; retrying {len(alts)} alternate ids")
    fetch(alts, cache)

    hits = 0
    with open(OUT / "track_features.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "track", "artist", "plays", "peak_year", "matched_id", "isrc"] + COLS)
        w.writeheader()
        for r in rows:
            cands = [sid(r["id"])] + [sid(u) for u in r["other_uris"].split("|") if u]
            m = next((c for c in cands if cache.get(c)), None)
            ft = cache.get(m) or {}
            hits += bool(m)
            w.writerow({"id": r["id"], "track": r["track"], "artist": r["artist"], "plays": r["plays"],
                        "peak_year": r["peak_year"], "matched_id": m or "", "isrc": ft.get("isrc", ""),
                        **{c: ft.get(c, "") for c in COLS}})
    print(f"TOTAL matched {hits}/{len(rows)} = {hits / len(rows):.0%} -> {OUT / 'track_features.csv'}")


if __name__ == "__main__":
    main()
