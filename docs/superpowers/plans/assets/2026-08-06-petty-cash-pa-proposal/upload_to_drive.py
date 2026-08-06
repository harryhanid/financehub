"""Uploads the proposal deck to Google Drive, converting it to a native
Google Slides file (not a passive .pptx) via the mimeType override."""
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import build_deck
import strip_bloat

HERE = os.path.dirname(__file__)
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
CREDENTIALS_PATH = os.path.join(HERE, "credentials.json")
TOKEN_PATH = os.path.join(HERE, "token.json")
RAW_PPTX = os.path.join(HERE, "petty-cash-pa-digital-proposal.pptx")
LITE_PPTX = os.path.join(HERE, "petty-cash-pa-digital-proposal-lite.pptx")
DECK_TITLE = "Digitalisasi Petty Cash & PA di Bawah Rp 10 Juta via PR Portal"


def _get_credentials():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
    return creds


def upload():
    build_deck.build(RAW_PPTX)
    strip_bloat.strip(RAW_PPTX, LITE_PPTX)

    service = build("drive", "v3", credentials=_get_credentials())
    file_metadata = {
        "name": DECK_TITLE,
        "mimeType": "application/vnd.google-apps.presentation",
    }
    media = MediaFileUpload(
        LITE_PPTX,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        resumable=False,
    )
    created = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    print("Created Google Slides file:")
    print("  id:", created["id"])
    print("  webViewLink:", created["webViewLink"])
    return created


if __name__ == "__main__":
    upload()
