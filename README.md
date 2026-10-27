# spotify-helper

A Claude Code plugin that walks you through turning your full Spotify listening history into:

| What | Skill | Changes your Spotify? |
|---|---|---|
| Export request and setup | spotify-start | No |
| A listening dashboard (one HTML file) | spotify-dashboard | No |
| Genre and mood tags for every song you love | spotify-enrich | No |
| A Liked Songs cleanup plus genre and vibe playlists | spotify-library | Yes, after a preview and your OK |

You don't need to know any code or use Terminal. Claude runs the scripts and asks you before anything in Spotify changes.

## What you need

- A Mac. Everything runs on your own computer, because the Spotify login and the mood data both need your machine and browser.
- A Claude subscription and either the Claude desktop app or Claude Code (see the two options below).
- Your Spotify "Extended streaming history" export. It takes a few days to arrive, so request it first (step 1 below).
- For the playlist and Liked Songs part only: a Spotify developer app. You can make your own (needs Premium), or a friend who has one can add you to theirs (up to 5 people).

## Set it up (pick one)

### Option A: a project in the Claude desktop app (no Terminal)

1. Download `spotify-helper.zip` (from whoever shared it, or Code > Download ZIP on this GitHub page) and unzip it.
2. Make a folder called `spotify-helper` in your home folder, and move the unzipped folder into it, renamed to `plugin`. You should end up with `~/spotify-helper/plugin/skills/`.
3. In the Claude desktop app, create a project (for example "Spotify") and add your `~/spotify-helper` folder to it.
4. Paste this into the project instructions:
   > Use the spotify-helper skills in plugin/skills/ in my spotify-helper folder, starting with plugin/skills/spotify-start/SKILL.md. Run every command on my Mac, never in the cloud.
5. Start a chat in the project and say "let's start the Spotify helper". Approve when Claude asks to connect to your computer.

### Option B: Claude Code

Install Claude Code (in Terminal: `curl -fsSL https://claude.ai/install.sh | bash`), run `claude`, then type:

```
/plugin marketplace add jakman91/spotify-helper
/plugin install spotify-helper@spotify-helper
```

Restart Claude Code, then say "let's start the Spotify helper". Using a zip instead of GitHub: unzip it and run `/plugin marketplace add <path to the unzipped folder>`.

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
