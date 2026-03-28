import os
import socket
import httplib2
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build, Resource

from models.google_token import GoogleToken


GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

def get_google_credentials(db: Session, user_id: int) -> Optional[Credentials]:
    token_record = db.query(GoogleToken).filter(GoogleToken.user_id == user_id).first()
    if not token_record:
        print(f"[GOOGLE SERVICE] No tokens found for user {user_id}")
        return None

    creds = Credentials(
        token=token_record.access_token,
        refresh_token=token_record.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=token_record.scopes
    )

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_record.access_token = creds.token
            token_record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600)
            db.commit()
            print(f"[GOOGLE SERVICE] Refreshed tokens for user {user_id}")
        except RefreshError as e:
            print(f"[GOOGLE SERVICE] Failed to refresh tokens for user {user_id}: {e}")
            return None

    return creds

def get_service(db: Session, user_id: int, service_name: str, version: str) -> Optional[Resource]:
    creds = get_google_credentials(db, user_id)
    if not creds:
        return None
    # Use standard initialization but with a temporary socket-level timeout
    # This ensures proxies/Certs are handled by the library internally (better for Windows)
    original_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(60)
        return build(service_name, version, credentials=creds)
    finally:
        socket.setdefaulttimeout(original_timeout)
