---
name: spotify-library
description: Clean up Spotify Liked Songs and build genre and vibe playlists from listening history. Use when someone wants to audit their library, add songs they love but never saved, remove rarely played saved songs, or create playlists like "my top indie rock" or "Sunday morning". Writes to Spotify only after a dry run and their OK.
---

# Liked Songs and playlists

Needs the Spotify app client ID (spotify-start step 3), `~/spotify-helper/data/tracks_all.json` (spotify-dashboard), and for playlists the genre and mood files (spotify-enrich).

Paths: `S="<this skill's base directory>/../../scripts"`, `W=~/spotify-helper`, `PY=~/.spotify-helper/venv/bin/python`. Start every Spotify command with `source ~/.spotify-helper/env &&`.

The first run of each kind of access (read, library write, playlist write) opens a browser tab to approve it. Tell them to expect it and click Agree. Tokens are saved in `~/.spotify-helper/`.

## Rules

- Every write script is a dry run unless given `--apply`. Always run the dry run, show the result, and get a clear yes first.
- Each write logs what it did next to its input file (`added_log.csv`, `removed_log.csv`, `created_playlists.csv`, `updated_log.csv`) so it can be undone.
- No playlist archiving or folders: the API can't do folders. If they want to tidy up, they drag playlists into a folder in the desktop app. `playlists.csv` marks stale ones to help.

## Part 1: audit (read-only)

```
source ~/.spotify-helper/env && $PY "$S/audit.py" "$W/data/tracks_all.json" "$W/audit"
```
Show `summary.md` as a short table. Key numbers: Liked Songs now, loved but not saved, saved with 3 or fewer plays. Re-run reports without calling Spotify with `--offline`; change thresholds with `--loved 10 --rare 3`.

## Part 2: Liked Songs

Ask what they want Liked Songs to be. Common answer: "everything I've loved", meaning songs with 10+ plays.

Add loved songs that aren't saved:
```
source ~/.spotify-helper/env && $PY "$S/add_saved.py" "$W/audit/loved_not_saved.csv" [--min-plays 10]
```
Show the count and top examples from the dry run, confirm, then re-run with `--apply`. Songs are added least-played first, so the most-played end up at the top of Liked Songs.

Remove rarely played saved songs (optional):
1. `$W/audit/remove_review.csv` lists saved songs with 3 or fewer plays, all marked `remove=yes`. Show them the list (or the first 30 and the total).
2. Ask which to keep. Recently added songs often have few plays because they're new, so point out anything added in the last few months. Set `remove` to `no` for keepers.
3. `source ~/.spotify-helper/env && $PY "$S/remove_saved.py" "$W/audit/remove_review.csv"`, show the dry run, confirm, then `--apply`.

## Part 3: genre playlists (top songs per genre, ranked by plays)

1. Using their genre buckets (`$W/genres/buckets.txt`) and per-genre counts, agree on which playlists to make and any splits. Write `$W/playlists/genre_playlists.json`:
   ```json
   [
     {"name": "Indie rock", "genres": ["Indie rock"]},
     {"name": "EDM: 2012-2016", "genres": ["EDM"], "peak_year_max": 2016},
     {"name": "EDM: now", "genres": ["EDM"], "peak_year_min": 2017},
     {"name": "Taylor Swift", "artists": ["Taylor Swift"], "size": null}
   ]
   ```
   Options: `genres`, `artists`, `exclude_artists`, `peak_year_min`, `peak_year_max`, `min_plays` (default 10), `size` (default 100; null for all).
2. Preview: `$PY "$S/genre_preview.py" "$W/data/tracks_all.json" "$W/genres/track_genres.json" "$W/playlists/genre_playlists.json" "$W/playlists/genre_preview.csv"`. Show each list's size and top artists. Iterate until they're happy.
3. Create: `source ~/.spotify-helper/env && $PY "$S/create_playlists.py" "$W/playlists/genre_preview.csv"`, confirm, then `--apply`. Playlists are private. Use `--only "Name"` to make just some.

## Part 4: vibe playlists (hand-picked by Claude)

These are for moods and activities: Sunday morning, workout, focus, dinner party, sad, summer. Claude picks the songs; this beats Spotify's own generators because it knows what they've actually loved.

1. Ask which vibes they want and, for each, a sentence on the feel plus 2 or 3 example artists or songs. Write their answers to `$W/playlists/vibes.md`.
2. For each vibe, pull a candidate pool with filters that fit, e.g.:
   ```
   $PY "$S/candidates.py" "$W/data/tracks_all.json" --genres "$W/genres/track_genres.json" --moods "$W/mood/track_moods.json" --mood Calm Happy --limit 400
   ```
   Filters: `--genre`, `--mood`, `--artist`, `--min-plays`. Run a few pools if the vibe crosses genres.
3. Pick about 100 songs per vibe from the pools using music knowledge, not just the tags. Order them so they flow. Avoid more than about 5 songs per artist unless asked. Write them to `$W/playlists/picks.txt`:
   ```
   ## Sunday Morning
   Sunday Morning | Maroon 5
   Banana Pancakes | Jack Johnson
   ```
4. Match to Spotify IDs: `$PY "$S/match_picks.py" "$W/data/tracks_all.json" "$W/playlists/picks.txt" "$W/playlists/vibe_preview.csv"`. Fix any MISS lines (usually a title spelled differently) and re-run.
5. Show each list as a short sample (first 15 and the artist mix). Take their edits, then create: `source ~/.spotify-helper/env && $PY "$S/create_playlists.py" "$W/playlists/vibe_preview.csv"`, confirm, `--apply`.

## Changing playlists later

To replace the songs in a playlist this created (and optionally rename it), edit the preview CSV, then:
```
source ~/.spotify-helper/env && $PY "$S/update_playlists.py" "$W/playlists/genre_preview.csv" "Old name=New name"
```
Use the same name on both sides to keep the name. It logs the old song list first.
