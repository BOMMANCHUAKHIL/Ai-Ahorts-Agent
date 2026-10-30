import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeUploader:
    """Handles OAuth and video uploads to YouTube."""

    def __init__(self, credentials_dir: str = "credentials"):
        self.credentials_dir = credentials_dir
        self.client_secret = os.path.join(
            credentials_dir, "client_secret.json"
        )
        self.token_path = os.path.join(
            credentials_dir, "token.pickle"
        )
        self.youtube = None

    def _authenticate(self):
        """Run once to get OAuth token. Subsequent runs reuse it."""
        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as f:
                creds = pickle.load(f)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_secret, SCOPES
                )
                creds = flow.run_local_server(port=8080)

            with open(self.token_path, "wb") as f:
                pickle.dump(creds, f)

        self.youtube = build("youtube", "v3", credentials=creds)

    def upload(self, video_path: str, title: str,
               description: str, tags: list = None,
               privacy: str = "public") -> str:
        """Upload a video. Returns the YouTube video ID."""

        if not self.youtube:
            self._authenticate()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],
                "tags": tags or ["shorts", "automation"],
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(
            video_path,
            chunksize=-1,  # Upload in one request for small files
            resumable=True,
            mimetype="video/mp4"
        )

        request = self.youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"    Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        print(f"    ✓ Uploaded: https://youtube.com/shorts/{video_id}")
        return video_id