#!/usr/bin/env python3
"""Fill mood-feature gaps and label moods for loved tracks.

Usage: python3 fill_moods.py <mood_dir> [--gaps]

Inputs in mood_dir: track_features.csv (mood_pull.py), and optionally
claude_estimates.txt (spotify_id|valence|energy|tempo|acousticness|instrumentalness|danceability).
--gaps only writes estimate_needed.csv: songs ReccoBeats missed whose artist has
fewer than 5 covered songs, so an artist median would be a poor guess. Claude
estimates those from music knowledge into claude_estimates.txt.
Gap order: ReccoBeats -> Claude estimate -> artist median -> overall median.
Output: track_moods.csv and track_moods.json (track id -> features, source, moods).
"""
import csv, json, statistics as st, sys
from collections import defaultdict
from pathlib import Path

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("mood")
F = ["valence", "energy", "tempo", "acousticness", "instrumentalness", "danceability"]

rows = list(csv.DictReader(open(D / "track_features.csv")))
est = {}
if (D / "claude_estimates.txt").exists():
    for line in open(D / "claude_estimates.txt"):
        p = line.strip().split("|")
        if len(p) == len(F) + 1:
            est[p[0]] = dict(zip(F, map(float, p[1:])))

by_artist = defaultdict(list)
for r in rows:
    if r["matched_id"]:
        for k in F:
            r[k] = float(r[k])
        r["source"] = "reccobeats"
        by_artist[r["artist"]].append(r)

if "--gaps" in sys.argv:
    need = [r for r in rows if not r["matched_id"] and len(by_artist[r["artist"]]) < 5
            and r["id"].rsplit(":", 1)[-1] not in est]
    with open(D / "estimate_needed.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["spotify_id", "track", "artist", "plays"])
        w.writerows([r["id"].rsplit(":", 1)[-1], r["track"], r["artist"], r["plays"]] for r in need)
    print(f"{len(need)} songs need estimates -> {D / 'estimate_needed.csv'}")
    sys.exit()

covered = [x for pool in by_artist.values() for x in pool]
for r in rows:
    if r["matched_id"]:
        continue
    sid = r["id"].rsplit(":", 1)[-1]
    if sid in est:
        r.update(est[sid]); r["source"] = "claude_estimate"
    else:
        pool = by_artist[r["artist"]] or covered
        r.update({k: round(st.median(x[k] for x in pool), 3) for k in F})
        r["source"] = "artist_median" if by_artist[r["artist"]] else "overall_median"
        if "live" in r["track"].lower():
            r["energy"] = min(1, r["energy"] + .05); r["acousticness"] = r["acousticness"]
        if "acoustic" in r["track"].lower():
            r["energy"] = max(0, r["energy"] - .25); r["acousticness"] = max(r["acousticness"], .7)


def pct(vals, q):
    s = sorted(vals); return s[int(q * (len(s) - 1))]


E_ = [r["energy"] for r in rows]; V = [r["valence"] for r in rows]
e20, e50, e75 = pct(E_, .2), pct(E_, .5), pct(E_, .75)
v25, v65 = pct(V, .25), pct(V, .65)
print(f"cutoffs: energy p20={e20:.2f} p50={e50:.2f} p75={e75:.2f}; valence p25={v25:.2f} p65={v65:.2f}")


def moods(r):
    v, e, t, a, i, d = (r[k] for k in ("valence", "energy", "tempo", "acousticness", "instrumentalness", "danceability"))
    m = []
    if e >= e75 and t >= 118: m.append("Hype")
    if v >= v65 and e >= e50: m.append("Happy")
    if v < v25 and e < e50: m.append("Sad")
    if v < .45 and e >= e75: m.append("Intense")
    if e < e20: m.append("Calm")
    if i >= .5: m.append("Instrumental")
    if d >= .7 and e >= e50: m.append("Dance")
    return m


out = {}
with open(D / "track_moods.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["id", "track", "artist", "plays", "source"] + F + ["moods"])
    for r in rows:
        m = moods(r)
        w.writerow([r["id"], r["track"], r["artist"], r["plays"], r["source"]] + [round(r[k], 3) for k in F] + ["|".join(m)])
        out[r["id"]] = {"src": r["source"], **{k[:3]: round(r[k], 3) for k in F}, "moods": m}
json.dump({"cutoffs": {"energy_p20": e20, "energy_p50": e50, "energy_p75": e75, "valence_p25": v25, "valence_p65": v65},
           "tracks": out}, open(D / "track_moods.json", "w"))

from collections import Counter
print(Counter(r["source"] for r in rows))
print(Counter(x for v in out.values() for x in v["moods"]))
print("no mood:", sum(1 for v in out.values() if not v["moods"]))
