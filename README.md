# spotify-helper

A Claude Code plugin that walks you through turning your full Spotify listening history into:

| What | Skill | Changes your Spotify? |
|---|---|---|
| Export request and setup | spotify-start | No |
| A listening dashboard (one HTML file) | spotify-dashboard | No |
| Genre and mood tags for every song you love | spotify-enrich | No |
| A Liked Songs cleanup plus genre and vibe playlists | spotify-library | Yes, after a preview and your OK |

You don't need to know any code. Claude runs the scripts and asks you before anything in Spotify changes.

## What you need

- A Mac. Everything runs locally, because the Spotify login and the mood data both need your own machine and browser.
- Claude Code with a Claude subscription. To install it, open Terminal and run `curl -fsSL https://claude.ai/install.sh | bash`.
- Your Spotify "Extended streaming history" export. It takes a few days to arrive, so request it first (step 1 below).
- For the playlist and Liked Songs part only: a Spotify developer app. You can make your own (needs Premium), or a friend who has one can add you to theirs (up to 5 people).

## Install

In Terminal, run `claude`, then type:

```
/plugin marketplace add jakman91/spotify-helper
/plugin install spotify-helper@spotify-helper
```

Restart Claude Code, then say "let's start the Spotify helper".

## How it goes

1. Request your export at spotify.com/account/privacy (tick "Extended streaming history"). Claude walks you through this and the rest of the setup while you wait.
2. When the email arrives, unzip it into `~/spotify-helper/export/` and ask for the dashboard.
3. Ask for genres and moods. Claude asks how you think about your music, tags your artists, and pulls mood data.
4. Ask to clean up Liked Songs and build playlists. You see every change before it happens.

Your data stays on your Mac in `~/spotify-helper/`. Settings and Spotify login tokens are in `~/.spotify-helper/`. Delete those two folders to remove everything.

## Notes

- Spotify's API can't create playlist folders. If you want to tidy old playlists, drag them into a folder in the Spotify desktop app. The audit marks which ones look stale.
- New Spotify developer apps get no genres or audio features from Spotify, so genres are tagged by Claude and moods come from [ReccoBeats](https://reccobeats.com) plus Claude's estimates.
- The dashboard bundles [d3](https://d3js.org) (ISC license) and the IBM Plex and Space Grotesk fonts (SIL Open Font License).
