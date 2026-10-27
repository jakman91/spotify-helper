#!/usr/bin/env python3
"""Read-only audit of a Spotify library and playlists against listening history.

Pulls Liked Songs and every playlist in your library, joins them to the
per-track history table (tracks_all.json from build_datasets.py), and writes
CSV reports plus a summary. It never changes anything in Spotify: the only
scopes it asks for are user-library-read, playlist-read-private and
playlist-read-collaborative.

Run:
    source ~/.spotify-helper/env
    ~/.spotify-helper/venv/bin/python audit.py tracks_all.json out/ [--loved 10] [--rare 3]

Outputs in out/:
    summary.md               headline numbers and suggested next steps
    library.csv              every saved track, its history stats, and a suggested action
    loved_not_saved.csv      tracks at or above the loved threshold missing from Liked Songs
    remove_review.csv        low-play saved songs with remove=yes, to edit before remove_saved.py
    playlists.csv            one row per playlist with size, % loved and a stale flag
    playlist_overlap.csv     pairs of playlists sharing at least half their tracks
    raw_library.json         the raw pull, so reports can be re-run offline with --offline
"""

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

from spotify_client import client, page_all


# ---------- matching ----------

def norm(s):
    """Lowercase, strip accents, drop '- Remastered 2011', '(feat. X)' and punctuation."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\s+-\s+.*$", "", s)
    s = re.sub(r"\((feat|with|ft)\.?[^)]*\)", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_history(path):
    rows = json.load(open(path))
    by_uri, by_key = {}, {}
    for r in rows:
        for u in [r["id"]] + [x for x in (r.get("other_uris") or "").split("|") if x]:
            by_uri[u] = r
        by_key.setdefault((norm(r["track"]), norm(r["artist"])), r)
    return rows, by_uri, by_key


def match(track, by_uri, by_key):
    r = by_uri.get(track["uri"])
    if r:
        return r, "uri"
    r = by_key.get((norm(track["name"]), norm(track["artist"])))
    return (r, "name") if r else (None, "")


# ---------- Spotify pull ----------

def simplify(t):
    if not t or t.get("type") not in (None, "track") or not t.get("uri"):
        return None  # podcast episode, local file without a URI, or removed track
    return {
        "uri": t["uri"],
        "name": t.get("name", ""),
        "artist": ", ".join(a["name"] for a in t.get("artists", [])),
        "album": (t.get("album") or {}).get("name", ""),
        "is_local": bool(t.get("is_local")),
    }


def pull(sp):
    me = sp.current_user()
    print(f"Signed in as {me.get('display_name') or me['id']}", file=sys.stderr)

    saved = []
    for it in page_all(sp, sp.current_user_saved_tracks(limit=50)):
        t = simplify(it.get("track") or it.get("item"))
        if t:
            t["added_at"] = it.get("added_at", "")
            saved.append(t)
    print(f"Liked Songs: {len(saved)}", file=sys.stderr)

    playlists = []
    for p in page_all(sp, sp.current_user_playlists(limit=50)):
        entry = {
            "id": p["id"],
            "name": p.get("name", ""),
            "owner_id": (p.get("owner") or {}).get("id", ""),
            "owner": (p.get("owner") or {}).get("display_name", ""),
            "public": p.get("public"),
            "collaborative": p.get("collaborative"),
            "description": p.get("description", ""),
            "tracks": [],
            "error": "",
        }
        try:
            for it in page_all(sp, sp.playlist_items(p["id"], limit=100, additional_types=("track",))):
                t = simplify(it.get("track") or it.get("item"))
                if t:
                    t["added_at"] = it.get("added_at", "")
                    entry["tracks"].append(t)
        except Exception as e:  # Spotify-owned or restricted playlists return 403/404
            entry["error"] = str(getattr(e, "http_status", "")) or type(e).__name__
        playlists.append(entry)
        time.sleep(0.05)
    print(f"Playlists: {len(playlists)}", file=sys.stderr)
    return {"user_id": me["id"], "pulled_at": datetime.now(timezone.utc).isoformat(),
            "saved": saved, "playlists": playlists}


# ---------- reports ----------

def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def years_since(iso):
    if not iso:
        return None
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return round((datetime.now(timezone.utc) - d).days / 365.25, 1)


def report(raw, history_path, out, loved_min, rare_max):
    rows, by_uri, by_key = load_history(history_path)
    os.makedirs(out, exist_ok=True)

    # Library: one row per saved track. History rows are deduped by name+artist,
    # so two saved versions of one song share a history row and count as a duplicate.
    lib, seen_hist = [], defaultdict(list)
    for t in raw["saved"]:
        h, how = match(t, by_uri, by_key)
        plays = h["plays"] if h else 0
        if h:
            seen_hist[h["id"]].append(t["uri"])
        if plays >= loved_min:
            action = "keep"
        elif plays <= rare_max:
            action = "remove candidate"
        else:
            action = "review"
        lib.append({**t, "plays": plays, "skip_rate": h["skip_rate"] if h else "",
                    "last_played": h["last"] if h else "", "matched_by": how,
                    "history_id": h["id"] if h else "", "action": action})
    for r in lib:
        r["duplicate"] = "yes" if r["history_id"] and len(seen_hist[r["history_id"]]) > 1 else ""
    lib.sort(key=lambda r: -r["plays"])
    write_csv(os.path.join(out, "library.csv"), lib,
              ["action", "plays", "name", "artist", "album", "skip_rate", "last_played",
               "added_at", "duplicate", "matched_by", "uri"])

    write_csv(os.path.join(out, "remove_review.csv"),
              [{**r, "remove": "yes"} for r in lib if r["action"] == "remove candidate"],
              ["remove", "plays", "name", "artist", "album", "last_played", "added_at", "uri"])

    loved = [r for r in rows if r["plays"] >= loved_min]
    missing = [r for r in loved if r["id"] not in seen_hist]
    missing.sort(key=lambda r: -r["plays"])
    write_csv(os.path.join(out, "loved_not_saved.csv"), missing,
              ["plays", "track", "artist", "album", "skip_rate", "first", "last", "peak_year", "id"])

    # Playlists
    saved_ids = set(seen_hist)
    loved_ids = {r["id"] for r in loved}
    pl_rows, pl_sets = [], {}
    for p in raw["playlists"]:
        ids, plays, unmatched = set(), [], 0
        for t in p["tracks"]:
            h, _ = match(t, by_uri, by_key)
            if h:
                ids.add(h["id"])
                plays.append(h["plays"])
            else:
                unmatched += 1
        pl_sets[p["id"]] = ids
        n = len(p["tracks"])
        last_add = max((t["added_at"] for t in p["tracks"] if t.get("added_at")), default="")
        median = sorted(plays)[len(plays) // 2] if plays else 0
        owned = p["owner_id"] == raw["user_id"]
        stale = (years_since(last_add) or 0) >= 2
        if p["error"]:
            suggestion = "unreadable"
        elif n == 0:
            suggestion = "empty"
        elif stale and median < loved_min:
            suggestion = "stale"
        else:
            suggestion = "active"
        pl_rows.append({
            "name": p["name"], "owned": "yes" if owned else "no", "owner": p["owner"],
            "tracks": n, "median_plays": median,
            "pct_in_library": round(100 * len(ids & saved_ids) / max(len(ids), 1)),
            "pct_loved": round(100 * len(ids & loved_ids) / max(len(ids), 1)),
            "never_played": unmatched + sum(1 for x in plays if x == 0),
            "last_added": last_add[:10], "years_since_add": years_since(last_add) or "",
            "status": suggestion, "error": p["error"], "id": p["id"],
        })
    pl_rows.sort(key=lambda r: (r["status"] != "active", -r["tracks"]))
    write_csv(os.path.join(out, "playlists.csv"), pl_rows,
              ["status", "name", "owned", "owner", "tracks", "median_plays", "pct_loved",
               "pct_in_library", "never_played", "last_added", "years_since_add", "error", "id"])

    names = {p["id"]: p["name"] for p in raw["playlists"]}
    pairs, keys = [], [k for k, v in pl_sets.items() if len(v) >= 5]
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            inter = len(pl_sets[a] & pl_sets[b])
            smaller = min(len(pl_sets[a]), len(pl_sets[b]))
            if inter and inter / smaller >= 0.5:
                pairs.append({"playlist_a": names[a], "playlist_b": names[b], "shared": inter,
                              "pct_of_smaller": round(100 * inter / smaller)})
    pairs.sort(key=lambda r: -r["pct_of_smaller"])
    write_csv(os.path.join(out, "playlist_overlap.csv"), pairs,
              ["playlist_a", "playlist_b", "shared", "pct_of_smaller"])

    count = lambda key, val: sum(1 for r in lib if r[key] == val)
    sug = lambda val: sum(1 for r in pl_rows if r["status"].startswith(val))
    summary = f"""# Spotify audit ({raw['pulled_at'][:10]})

| Measure | Count |
|---|---|
| Liked Songs now | {len(lib)} |
| Saved and loved ({loved_min}+ plays) | {count('action', 'keep')} |
| Saved, {rare_max + 1}-{loved_min - 1} plays (review) | {count('action', 'review')} |
| Saved, {rare_max} or fewer plays (remove candidates) | {count('action', 'remove candidate')} |
| Saved twice (two versions of one song) | {sum(1 for r in lib if r['duplicate'])} |
| Loved but not saved | {len(missing)} |
| Liked Songs if trimmed to the loved set | {len(loved)} |
| Playlists in library | {len(pl_rows)} |
| Playlists still active | {sug('active')} |
| Playlists stale or empty | {sug('stale') + sug('empty')} |
| Playlists that could not be read | {sug('unreadable')} |
| Playlist pairs sharing 50%+ of tracks | {len(pairs)} |

Stale: no track added in 2+ years and median track plays under {loved_min}. Spotify's API can't
manage playlist folders, so sorting stale playlists into a folder is done by hand in the app.
Nothing was changed in Spotify. Adding and removing songs are separate steps that need your sign-off.
"""
    open(os.path.join(out, "summary.md"), "w").write(summary)
    print(summary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("history", help="tracks_all.json from build_datasets.py")
    ap.add_argument("out", help="output folder")
    ap.add_argument("--loved", type=int, default=10, help="plays needed to count as loved (default 10)")
    ap.add_argument("--rare", type=int, default=3, help="max plays for a remove candidate (default 3)")
    ap.add_argument("--offline", action="store_true", help="reuse out/raw_library.json instead of calling Spotify")
    a = ap.parse_args()

    raw_path = os.path.join(a.out, "raw_library.json")
    if a.offline:
        raw = json.load(open(raw_path))
    else:
        raw = pull(client())
        os.makedirs(a.out, exist_ok=True)
        json.dump(raw, open(raw_path, "w"))
    report(raw, a.history, a.out, a.loved, a.rare)


if __name__ == "__main__":
    main()
