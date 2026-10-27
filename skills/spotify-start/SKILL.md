---
name: spotify-start
description: START HERE for the Spotify helper; the only skill a person needs to run. Starts or resumes the whole workflow. Use when someone wants to analyze their Spotify listening history, clean up Liked Songs, or build playlists from it, or asks "what's next" in that workflow. Checks progress, handles the export request and Spotify app setup, and routes to the other spotify-* skills.
---

# Spotify helper: start here

This is the entry point. A person only ever needs to run this skill; it routes them to the others when it is time.

This walks someone through four stages, usually across a few sessions:

| Stage | Skill | Needs | Changes Spotify? |
|---|---|---|---|
| 1. Export + setup | spotify-start (this one) | Spotify account | No |
| 2. Dashboard | spotify-dashboard | The export | No |
| 3. Genres and moods | spotify-enrich | Dashboard data | No |
| 4. Liked Songs and playlists | spotify-library | Spotify app + stage 3 | Yes, only after a dry run and their OK |

Every command runs on the person's own Mac. ReccoBeats (moods) and the Spotify login both need their machine and browser. There are two ways to get there, and the skills work the same in both:

- Claude Code on the Mac, with the plugin installed. Commands run directly.
- A project in the Claude desktop app, with the plugin zip uploaded through the app's Plugins menu. Claude runs each command on the Mac through a session on their computer (they approve the prompt to connect it). Never run the scripts in a cloud container: the Spotify login can't reach their browser and ReccoBeats isn't reachable.

## Paths

- Scripts: the `scripts/` folder of this plugin, two levels up from this skill's base directory. Use `S="<this skill's base directory>/../../scripts"` in commands. Commands need the scripts on the Mac itself: if that path isn't on the Mac where commands run (for example, the plugin lives in the Claude app while commands run on their computer), first copy this plugin's `scripts/` folder, including `scripts/dashboard/`, to `~/spotify-helper/scripts/` on the Mac and use `S=~/spotify-helper/scripts`.
- Workspace: `~/spotify-helper/` (export, data, outputs). Private settings and login tokens: `~/.spotify-helper/`.

## Each time this skill runs

1. Run `python3 "$S/status.py"` and tell the person where they are in two or three sentences.
2. Pick up at the first unchecked step below, or hand off to the stage skill it names.

## Step 1: request the export (do this first, it takes days)

The normal "Account data" export is not enough. They need the Extended streaming history, which covers every play since the account was opened.

Tell them:
1. Go to https://www.spotify.com/account/privacy/ and sign in.
2. Under "Download your data", tick Extended streaming history (untick the others to make it faster), then Request data.
3. Confirm from the email Spotify sends right away.
4. Spotify says up to 30 days; it often arrives in a few days. The email has a ZIP called `my_spotify_data.zip`.
5. When it arrives, unzip it into `~/spotify-helper/export/` (any folder layout under there works).

While they wait, do steps 2 and 3 so everything else is ready.

## Step 2: install the tools

Run `bash "$S/setup.sh"`. It creates `~/.spotify-helper/venv` with spotipy 2.26.0 and the workspace folders. If it says Python is missing, have them run `xcode-select --install`, then re-run.

## Step 3: Spotify developer app

Stages 1 to 3 don't need this. Stage 4 does, because Spotify's API needs an app to sign in through. Two options:

A. Use a friend's app (simplest). An app owner can allowlist up to 5 people. The owner adds them at developer.spotify.com/dashboard > their app > User Management (name + the email on their Spotify account), then shares the app's Client ID. Nothing else is shared; there is no secret.

B. Make their own app. Requires Spotify Premium on the account that owns the app.
1. Go to https://developer.spotify.com/dashboard, sign in, accept the terms, and click Create app.
2. Name and description: anything (e.g. "Library helper").
3. Redirect URI: `http://127.0.0.1:8888/callback` (exactly this, then click Add).
4. Under "Which API/SDKs are you planning to use?", tick Web API. Save.
5. Open the app's Settings and copy the Client ID.

Then save it: `bash "$S/setup.sh" <CLIENT_ID>`. This writes `~/.spotify-helper/env`. Never ask for or store a client secret; the scripts use PKCE and don't need one.

## Then

- Export is in: use spotify-dashboard.
- Dashboard built: use spotify-enrich.
- Genres and moods done: use spotify-library.

## Ground rules for every stage

- Anything that changes Spotify runs as a dry run first, shows the person what would change, and waits for a clear yes before `--apply`.
- Every write logs what it changed (CSV next to its input) so it can be undone.
- Spotify's API can't create or move playlist folders. If they want to tidy old playlists, they drag them into a folder in the desktop app themselves; the audit's `playlists.csv` marks which look stale.
- New Spotify apps get no genres, audio features or recommendations from the API. That is why genres are tagged by Claude and moods come from ReccoBeats.
- Login tokens expire about 6 months after sign-in. If a script fails with an auth error later, delete the matching `~/.spotify-helper/token-*.json` and run it again to sign in.
