"""YouTube Data API login and helpers shared by every uploader (drama/youtube_upload.py, mv/youtube_upload.py) and
dreamfab/youtube_playlists.py.

Credentials: YT_CLIENT_SECRET = an OAuth client of type "Desktop app" (default
~/.config/dreamfab/youtube_client_secret.json; ~/.config/dreamfab/ from before the merge is still read when the
new folder has none); the login is cached next to it as youtube_token.json. Keep both outside the repo.
YT_CHANNEL_ID (optional) = the only channel a script may act on.
"""
import os, sys, time

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]


def _secret():
    if os.environ.get("YT_CLIENT_SECRET"):
        return os.environ["YT_CLIENT_SECRET"]
    for d in ("dreamfab", "autoip-mv-maker"):   # the second: where the MV and drama tools kept it before the merge
        p = os.path.expanduser(f"~/.config/{d}/youtube_client_secret.json")
        if os.path.exists(p):
            return p
    return os.path.expanduser("~/.config/dreamfab/youtube_client_secret.json")


SECRET = _secret()
TOKEN = os.path.join(os.path.dirname(SECRET), "youtube_token.json")


def youtube():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    if not os.path.exists(SECRET):
        sys.exit(f"no OAuth client at {SECRET} (docs/*/PUBLISHING.md: automatic upload)")
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES) if os.path.exists(TOKEN) else None
    if creds and not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:   # revoked, or a consent screen left in Testing (logins expire after 7 days)
            print("  login expired:", e)
            creds = None
    if not creds or not creds.valid:
        print("  log in with the channel's Google account (if the account owns several channels, pick the right one);")
        print("  if no browser opens, open the URL below in a browser on this computer")
        creds = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES).run_local_server(port=0, prompt="consent")
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def channel(yt, lock=False, expect=None):
    """Print the logged-in channel; with lock=True exit unless it is `expect` (an upload plan's channel) or
    YT_CHANNEL_ID, whichever is set."""
    ch = yt.channels().list(part="snippet,contentDetails", mine=True).execute()["items"][0]
    print(f"  channel     {ch['snippet']['title']} ({ch['id']})")
    want = expect or os.environ.get("YT_CHANNEL_ID")
    if lock and want and ch["id"] != want:
        sys.exit(f"  !! logged in to channel {ch['id']}, expected {want}: delete {TOKEN} and log in again, "
                 "picking the right channel")
    return ch


def wait_until(check, what, timeout=45, step=3):
    """Reads lag a few seconds behind writes: poll check() until it is true. Returns False (and says so) on timeout."""
    end = time.time() + timeout
    while True:
        if check():
            return True
        if time.time() > end:
            print(f"  !! {what}: still not visible after {timeout} s; check in YouTube Studio")
            return False
        time.sleep(step)


def in_playlist(yt, pid, vid):
    return bool(yt.playlistItems().list(part="id", playlistId=pid, videoId=vid).execute()["items"])
