import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load_credentials(client_secrets_file: Path, token_file: Path):
    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_file), SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.parent.mkdir(parents=True, exist_ok=True)
        token_file.write_text(creds.to_json())
    return creds


def upload_video(metadata_path: Path):
    metadata = json.loads(metadata_path.read_text())
    video_path = Path(metadata["video_path"])
    client_secrets_file = Path(os.environ["YOUTUBE_CLIENT_SECRETS_FILE"])
    token_file = Path(os.environ.get("YOUTUBE_TOKEN_FILE", ".secrets/youtube-token.json"))

    if not client_secrets_file.exists():
        raise FileNotFoundError(f"client secrets 파일이 없습니다: {client_secrets_file}")
    if not video_path.exists():
        raise FileNotFoundError(f"업로드할 영상이 없습니다: {video_path}")

    creds = load_credentials(client_secrets_file, token_file)
    youtube = build("youtube", "v3", credentials=creds)

    request_body = {
        "snippet": {
            "title": metadata.get("title", video_path.stem),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
            "categoryId": "25",
        },
        "status": {
            "privacyStatus": metadata.get("privacy_status", os.environ.get("YOUTUBE_PRIVACY_STATUS", "private")),
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    uploaded = {
        "video_id": response["id"],
        "url": f"https://www.youtube.com/watch?v={response['id']}",
    }
    output_path = metadata_path.with_suffix(".uploaded.json")
    output_path.write_text(json.dumps(uploaded, ensure_ascii=False, indent=2))
    print(json.dumps(uploaded, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    metadata_path = os.environ.get("SHORTS_METADATA_FILE")
    if not metadata_path:
        raise RuntimeError("SHORTS_METADATA_FILE 환경변수가 필요합니다.")
    upload_video(Path(metadata_path))
