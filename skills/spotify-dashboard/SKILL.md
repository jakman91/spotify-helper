---
name: spotify-dashboard
description: Build a personal Spotify listening dashboard (one HTML file) from an Extended Streaming History export. Use when someone has their Spotify export and wants to see their listening stats, top artists and songs by year, or habits, or wants to rebuild the dashboard after adding genres or moods. Usually reached from spotify-start; if someone is new or unsure where they are, run spotify-start first.
---

# Spotify listening dashboard

Turns the export into a single HTML file with tabs for Overview, Top lists, Library builder and Habits, plus Genres and Moods once spotify-enrich has run. Read-only; no Spotify login needed.

Paths: `S="<this skill's base directory>/../../scripts"`, workspace `W=~/spotify-helper`, Python `PY=~/.spotify-helper/venv/bin/python` (plain `python3` also works for this stage).

## Steps

1. Check the export is there: `ls "$W/export"`. The files that matter are `Streaming_History_Audio_*.json`. If they only see `StreamingHistory_music_*.json` (no "Audio"), that's the short one-year export; send them back to spotify-start step 1 for the Extended one.
2. Ask what name to put in the title (default "Your Spotify").
3. Build the datasets. The time zone defaults to this Mac's; pass `--tz America/New_York` style if they lived elsewhere most of the time.
   ```
   $PY "$S/build_datasets.py" "$W/export" "$W/data"
   ```
   If `$W/genres/track_genres.json` exists add `--track-genres "$W/genres/track_genres.json"`. If `$W/mood/track_moods.json` exists add `--track-moods "$W/mood/track_moods.json"`.
4. Render and open it:
   ```
   $PY "$S/render_dashboard.py" "$W/data" "$W/dashboard.html" --name "Sam"
   open "$W/dashboard.html"
   ```
5. Share 3 to 5 highlights from the build output and `$W/data/summary.json` and `yearly.json`: total hours, top artist, biggest year, how taste shifted. Keep it short.
6. Point them to the next step: spotify-enrich adds Genres and Moods tabs and is needed for playlists.

## Definitions (if they ask)

- Play: a music stream of 30 seconds or more, Spotify's own threshold. Podcasts and audiobooks are excluded.
- Skip rate: starts that ended under 30 seconds or were flagged skipped, out of all starts.
- Songs are merged by title + artist; the most-played version's Spotify ID is kept and the others go in `other_uris`.
- Loved: 10+ plays. Later stages use this as the default bar.

`$W/data/tracks_all.json` and `tracks_all.csv` (every song with plays, skip rate, peak year and plays per year) feed every later stage.
