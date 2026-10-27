#!/usr/bin/env python3
"""Turn hand-picked playlists (picks.txt) into a preview CSV with Spotify URIs.

    python3 match_picks.py tracks_all.json playlists/picks.txt playlists/vibe_preview.csv

picks.txt format, one song per line under a "## Playlist name" heading:

    ## Sunday Morning
    Sunday Morning | Maroon 5
    Banana Pancakes | Jack Johnson

Each line is matched to the listening history (title + artist, forgiving
about "- Remastered", "(feat. X)" and accents), preferring the most-played
version. Lines that don't match are printed as MISS so they can be fixed.
"""

import csv
import json
import re
import sys
import unicodedata


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = s.replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def base(t):  # strip " - Live ..." / "- Remaster" suffixes
    return norm(re.split(r" - |\s\((?:feat|with|live|remaster|single|radio)", t, flags=re.I)[0])


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    T = json.load(open(sys.argv[1]))
    for r in T:
        r["_n"], r["_b"], r["_a"] = norm(r["track"]), base(r["track"]), norm(r["artist"])

    lists, cur = [], None
    for line in open(sys.argv[2]):
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.startswith("## "):
            cur = (line[3:].strip(), [])
            lists.append(cur)
            continue
        if cur is None or " | " not in line:
            print(f"SKIP (not 'title | artist' under a ## heading): {line}")
            continue
        t, a = line.rsplit(" | ", 1)
        cur[1].append((t.strip(), a.strip()))

    def find(t, a):
        nt, bt, na = norm(t), base(t), norm(a)
        cand = [r for r in T if r["_a"] == na or r["_a"].startswith(na) or (na.startswith(r["_a"]) and len(r["_a"]) > 3)]
        ex = [r for r in cand if r["_n"] == nt or r["_b"] == bt or r["_n"].startswith(nt + " ")]
        if not ex:
            ex = [r for r in cand if nt in r["_n"]]
        alt = re.compile(r"remix|mix\b|acoustic", re.I)
        ex = [r for r in ex if not alt.search(r["track"]) or alt.search(t)] or ex
        return sorted(ex, key=lambda r: -r["plays"])

    out, miss, seen = [], [], set()
    for name, items in lists:
        rank = 0
        for t, a in items:
            c = find(t, a)
            c = [x for x in c if (name, x["id"]) not in seen]
            if not c:
                miss.append((name, t, a))
                continue
            r = c[0]
            seen.add((name, r["id"]))
            rank += 1
            out.append([name, rank, r["track"], r["artist"], r["plays"], r["peak_year"], r["id"]])

    with open(sys.argv[3], "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["playlist", "rank", "track", "artist", "plays", "peak_year", "uri"])
        w.writerows(out)
    for name, items in lists:
        print(f"{name}: {sum(1 for o in out if o[0] == name)} of {len(items)} matched")
    for m in miss:
        print("MISS", " | ".join(m))
    print(f"-> {sys.argv[3]}")


if __name__ == "__main__":
    main()
