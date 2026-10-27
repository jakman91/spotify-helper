"""Shared Spotify login for every script that calls the Web API.

Uses PKCE, so only the app's client ID is needed (no client secret). Each
kind of access gets its own token file, so read-only steps never hold write
permission. Tokens live in ~/.spotify-helper/ with owner-only permissions.

Needs SPOTIPY_CLIENT_ID and SPOTIPY_REDIRECT_URI in the environment
(run `source ~/.spotify-helper/env` first).
"""

import os

HOME = os.path.expanduser("~/.spotify-helper")

ACCESS = {
    "read": ("user-library-read playlist-read-private playlist-read-collaborative", "token-read.json"),
    "library-write": ("user-library-read user-library-modify", "token-library-write.json"),
    "playlist-write": ("playlist-read-private playlist-modify-private playlist-modify-public", "token-playlist-write.json"),
}


def client(access="read"):
    import spotipy
    from spotipy.cache_handler import CacheFileHandler
    from spotipy.oauth2 import SpotifyPKCE

    if not os.environ.get("SPOTIPY_CLIENT_ID"):
        raise SystemExit("SPOTIPY_CLIENT_ID is not set. Run: source ~/.spotify-helper/env")
    scopes, token_file = ACCESS[access]
    token_path = os.path.join(HOME, token_file)
    os.makedirs(HOME, mode=0o700, exist_ok=True)
    auth = SpotifyPKCE(scope=scopes, cache_handler=CacheFileHandler(cache_path=token_path),
                       open_browser=True)
    sp = spotipy.Spotify(auth_manager=auth, retries=5, status_retries=5, backoff_factor=0.5)
    sp.current_user()
    if os.path.exists(token_path):
        os.chmod(token_path, 0o600)
    return sp


def page_all(sp, first):
    page = first
    while page:
        yield from page["items"]
        page = sp.next(page) if page.get("next") else None
