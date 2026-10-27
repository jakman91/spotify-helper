---
name: spotify-enrich
description: Add genres and moods to someone's Spotify listening history. Use after the spotify-dashboard step, when they want genre or mood breakdowns, or before building genre or vibe playlists. Claude tags artists into the person's own genre buckets and pulls mood features from ReccoBeats.
---

# Genres and moods

Spotify's API gives new apps no genres and no audio features, so:
- Genres: Claude tags each artist into genre buckets the person chooses. Songs inherit their artist's genre.
- Moods: audio features (energy, valence, tempo, etc.) come from ReccoBeats, a free API with no key. Claude estimates the gaps.

Read-only; no Spotify login. Needs `~/spotify-helper/data/tracks_all.json` from spotify-dashboard.

Paths: `S="<this skill's base directory>/../../scripts"`, `W=~/spotify-helper`, `PY=~/.spotify-helper/venv/bin/python`.

## Part 1: genres

1. Look at their top 40 artists so the buckets fit them:
   ```
   $PY -c "import json; [print(a['plays'], a['artist']) for a in json.load(open('$HOME/spotify-helper/data/artists.json'))[:40]]"
   ```
2. Interview briefly (one message, not a questionnaire): which genres do they listen to, and do any need splitting? Common splits: a big genre by era (2010s EDM vs now), by style (90s alt vs emo), or one favorite artist as its own bucket. Propose 8 to 15 buckets based on their top artists and let them adjust.
3. Save the bucket list to `$W/genres/buckets.txt`, one per line.
4. List artists to tag (artists with at least one loved song, 10+ plays):
   ```
   $PY "$S/genres.py" todo "$W/data/tracks_all.json" "$W/genres/artist_genres.json" "$W/genres/artists_to_tag.csv"
   ```
5. Tag them. Read `artists_to_tag.csv` in chunks of about 150 rows and add each artist to `$W/genres/artist_genres.json` as `{"Artist": "Bucket"}`, using only names from `buckets.txt`. Use music knowledge and the sample song titles. One bucket per artist. If an artist truly spans two, pick where most of their loved songs fit. Merge into the existing file each chunk; never overwrite earlier tags. Re-run `todo` to confirm the list is empty.
6. Apply and review:
   ```
   $PY "$S/genres.py" apply "$W/data/tracks_all.json" "$W/genres/artist_genres.json" "$W/genres/track_genres.json"
   ```
   Show the per-genre counts. Ask if any look wrong or too big/small; fix by editing tags or buckets and re-running apply. If they disagree with a specific artist, just change it.

## Part 2: moods

1. Pull features from ReccoBeats for loved songs. Takes about 2 to 5 minutes per 1,000 songs; it caches, so it can be re-run:
   ```
   $PY "$S/mood_pull.py" "$W/data/tracks_all.csv" "$W/mood"
   ```
   Expect roughly 60 to 75% of songs matched.
2. Find gaps worth estimating (missed songs by artists with fewer than 5 covered songs):
   ```
   $PY "$S/fill_moods.py" "$W/mood" --gaps
   ```
3. Estimate those from music knowledge into `$W/mood/claude_estimates.txt`, one line per song:
   `spotify_id|valence|energy|tempo|acousticness|instrumentalness|danceability`
   Values 0 to 1 except tempo (BPM). Work in chunks of about 150 from `estimate_needed.csv`, appending. Be honest about uncertainty by staying near middle values (0.4 to 0.6) for songs you don't know.
4. Label moods:
   ```
   $PY "$S/fill_moods.py" "$W/mood"
   ```
   Moods are multi-label and relative to their own library (percentile cutoffs): Happy, Calm, Hype, Sad, Intense, Instrumental, Dance.

## Finish

Rebuild the dashboard with both files (see spotify-dashboard step 3 and 4) so the Genres and Moods tabs appear, and open it. Then point them to spotify-library.
