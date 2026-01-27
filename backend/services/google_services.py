import os
import json
import base64
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build, Resource

from models.google_token import GoogleToken

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

def get_google_credentials(db: Session, user_id: int) -> Optional[Credentials]:
    """
    Retrieves and refreshes Google OAuth credentials for a user.
    """
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
            # Update database with new access token
            token_record.access_token = creds.token
            token_record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=3600) # Default expiry
            db.commit()
            print(f"[GOOGLE SERVICE] Refreshed tokens for user {user_id}")
        except RefreshError as e:
            print(f"[GOOGLE SERVICE] Failed to refresh tokens for user {user_id}: {e}")
            return None

    return creds

def get_service(db: Session, user_id: int, service_name: str, version: str) -> Optional[Resource]:
    """Generic function to get a Google API service."""
    creds = get_google_credentials(db, user_id)
    if not creds:
        return None
    return build(service_name, version, credentials=creds)

# --- CALENDAR TOOLS ---

async def check_calendar_availability(db: Session, user_id: int, parameters: dict) -> dict:
    days = int(parameters.get("days", 7))
    service = get_service(db, user_id, 'calendar', 'v3')
    if not service: return {"error": "Google Calendar not connected"}
    now = datetime.now(timezone.utc)
    result = service.freebusy().query(body={"timeMin": now.isoformat(), "timeMax": (now + timedelta(days=days)).isoformat(), "items": [{"id": "primary"}]}).execute()
    return {"status": "success", "busy": result.get('calendars', {}).get('primary', {}).get('busy', [])}

async def schedule_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'calendar', 'v3')
    if not service: return {"error": "Google Calendar not connected"}
    event = {
        'summary': parameters.get('title', 'Meeting'),
        'description': parameters.get('description', ''),
        'start': {'dateTime': parameters.get('start_time'), 'timeZone': 'UTC'},
        'end': {'dateTime': parameters.get('end_time'), 'timeZone': 'UTC'},
        'attendees': [{'email': parameters.get('attendee_email')}] if parameters.get('attendee_email') else []
    }
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return {"status": "success", "event_id": created_event.get('id'), "link": created_event.get('htmlLink')}

async def update_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'calendar', 'v3')
    if not service: return {"error": "Google Calendar not connected"}
    event_id = parameters.get("event_id")
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    if parameters.get('title'): event['summary'] = parameters.get('title')
    if parameters.get('start_time'): event['start'] = {'dateTime': parameters.get('start_time'), 'timeZone': 'UTC'}
    if parameters.get('end_time'): event['end'] = {'dateTime': parameters.get('end_time'), 'timeZone': 'UTC'}
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    return {"status": "success", "event_id": updated_event.get('id')}

async def delete_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'calendar', 'v3')
    if not service: return {"error": "Google Calendar not connected"}
    service.events().delete(calendarId='primary', eventId=parameters.get("event_id")).execute()
    return {"status": "success", "message": "Event deleted"}

# --- GMAIL TOOLS ---

async def send_email(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'gmail', 'v1')
    if not service: return {"error": "Gmail not connected"}
    
    from email.mime.text import MIMEText
    
    to_val = parameters.get("to_email")
    if isinstance(to_val, list):
        to_email = ", ".join(to_val)
    else:
        to_email = str(to_val)
        
    if not to_email or to_email.strip() == "":
        return {"error": "No recipient email address provided"}
        
    message = MIMEText(parameters.get("body", ""))
    message['to'] = to_email
    message['subject'] = parameters.get("subject", "")
    
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    sent_message = service.users().messages().send(userId='me', body={'raw': raw}).execute()
    return {"status": "success", "message_id": sent_message.get('id'), "recipients": to_email}

async def read_emails(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'gmail', 'v1')
    if not service: return {"error": "Gmail not connected"}
    results = service.users().messages().list(userId='me', q=parameters.get("query", ""), maxResults=parameters.get("max_results", 10)).execute()
    emails = []
    for msg in results.get('messages', []):
        m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        headers = {h['name']: h['value'] for h in m.get('payload', {}).get('headers', [])}
        emails.append({"id": msg['id'], "subject": headers.get('Subject'), "from": headers.get('From'), "snippet": m.get('snippet')})
    return {"status": "success", "emails": emails}

async def delete_email(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'gmail', 'v1')
    if not service: return {"error": "Gmail not connected"}
    service.users().messages().trash(userId='me', id=parameters.get("message_id")).execute()
    return {"status": "success", "message": "Email moved to trash"}

async def update_email_labels(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'gmail', 'v1')
    if not service: return {"error": "Gmail not connected"}
    body = {
        "addLabelIds": parameters.get("add_labels", []),
        "removeLabelIds": parameters.get("remove_labels", [])
    }
    service.users().messages().modify(userId='me', id=parameters.get("message_id"), body=body).execute()
    return {"status": "success"}

# --- DRIVE TOOLS ---

async def list_drive_files(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    
    query_parts = []
    
    # Use explicit filename if provided
    filename = parameters.get("filename")
    if filename:
        # Escape single quotes in filename
        safe_filename = filename.replace("'", "\\'")
        # Using 'contains' instead of '=' to allow for files with extensions 
        # or partial matches (e.g. "Resume" matches "Resume.pdf")
        query_parts.append(f"name contains '{safe_filename}'")
    
    # Use explicit mime_type if provided
    mime_type = parameters.get("mime_type")
    if mime_type:
        query_parts.append(f"mimeType = '{mime_type}'")
    
    # If a raw query is provided, use it but be careful
    raw_query = parameters.get("query")
    if raw_query:
        # Fix common LLM mistake: Google Drive API v3 uses 'name', not 'title'
        raw_query = raw_query.replace("title ", "name ").replace("title=", "name=")
        
        # Check if it looks like a structured query (contains =, contains, in, or has '')
        # If it doesn't, treat it as a fuzzy name search to prevent API errors
        if any(keyword in raw_query for keyword in ["=", "contains", "in", "mimeType", "name"]):
            query_parts.append(raw_query)
        else:
            safe_query = raw_query.replace("'", "\\'")
            query_parts.append(f"name contains '{safe_query}'")
        
    final_query = " and ".join(query_parts) if query_parts else None
    
    print(f"[GOOGLE DRIVE] Listing files with query: {final_query}")
    
    results = service.files().list(
        pageSize=parameters.get("page_size", 10), 
        q=final_query,
        fields="nextPageToken, files(id, name, mimeType, webViewLink)"
    ).execute()
    return {"status": "success", "files": results.get('files', [])}

async def upload_to_drive(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    from googleapiclient.http import MediaByteArrayUpload
    media = MediaByteArrayUpload(parameters.get('content', '').encode(), mime_type='text/plain')
    file = service.files().create(body={'name': parameters.get('filename')}, media_body=media).execute()
    return {"status": "success", "file_id": file.get('id')}

async def update_drive_file(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    updated = service.files().update(fileId=parameters.get("file_id"), body={'name': parameters.get('filename')}).execute()
    return {"status": "success", "file_id": updated.get('id')}

async def delete_drive_file(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    service.files().delete(fileId=parameters.get("file_id")).execute()
    return {"status": "success", "message": "File deleted"}

async def read_drive_file_content(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    file_id = parameters.get("file_id")
    try:
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime_type = file_metadata.get("mimeType")
        
        if mime_type == "application/vnd.google-apps.document":
            # Google Doc - export to text
            content = service.files().export(fileId=file_id, mimeType='text/plain').execute()
            return {"status": "success", "content": content.decode('utf-8'), "name": file_metadata.get("name")}
        elif mime_type.startswith("text/"):
            # Text file
            content = service.files().get_media(fileId=file_id).execute()
            return {"status": "success", "content": content.decode('utf-8'), "name": file_metadata.get("name")}
        elif mime_type == "application/pdf":
            # PDF - Use OCR via temporary Google Doc conversion
            return await read_drive_pdf_content(db, user_id, file_id, file_metadata.get("name"))
        else:
            return {"status": "error", "message": f"Reading content of type '{mime_type}' is not yet supported directly. Only Google Docs, PDFs, and text files can be read."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def read_drive_pdf_content(db: Session, user_id: int, file_id: str, file_name: str) -> dict:
    """Extract text from PDF using Google Drive OCR (Convert to Doc)"""
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    
    try:
        # 1. Create a copy of the PDF as a Google Doc (this triggers OCR)
        doc_metadata = {
            'name': f"TEMP_OCR_{file_name}",
            'mimeType': 'application/vnd.google-apps.document'
        }
        temp_doc = service.files().copy(
            fileId=file_id,
            body=doc_metadata,
            fields='id'
        ).execute()
        temp_doc_id = temp_doc.get('id')
        
        # 2. Export the temp doc as plain text
        content = service.files().export(
            fileId=temp_doc_id,
            mimeType='text/plain'
        ).execute()
        
        # 3. Delete the temporary doc
        service.files().delete(fileId=temp_doc_id).execute()
        
        return {
            "status": "success", 
            "content": content.decode('utf-8'), 
            "name": file_name,
            "is_pdf": True,
            "file_id": file_id
        }
    except Exception as e:
        return {"status": "error", "message": f"PDF OCR failed: {str(e)}"}

async def get_drive_file_link(db: Session, user_id: int, file_id: str) -> dict:
    """Get a webViewLink for the file or prepare content for proxy"""
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    try:
        file = service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()
        return {"status": "success", "link": file.get('webViewLink')}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- SHEETS TOOLS ---

async def create_spreadsheet(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'sheets', 'v4')
    if not service: return {"error": "Google Sheets not connected"}
    spreadsheet = {'properties': {'title': parameters.get('title', 'New Sheet')}}
    result = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
    return {"status": "success", "spreadsheet_id": result.get('spreadsheetId')}

async def read_spreadsheet(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'sheets', 'v4')
        if not service: return {"error": "Google Sheets not connected"}
        
        spreadsheet_id = parameters.get("spreadsheet_id")
        user_range = parameters.get("range")
        
        # If range is specified, try reading it directly
        if user_range:
            try:
                result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=user_range).execute()
                return {"status": "success", "values": result.get('values', [])}
            except Exception as e:
                print(f"[RECOVERABLE ERROR] Failed to read specific range '{user_range}': {e}. Falling back to first sheet.")
        
        # Fallback or Default: Fetch spreadsheet metadata to find the first sheet name
        spread_meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spread_meta.get('sheets', [])
        if not sheets:
            return {"error": "No sheets found in spreadsheet"}
            
        first_sheet_name = sheets[0].get('properties', {}).get('title', 'Sheet1')
        print(f"[LOGGER] Defaulting to first sheet: {first_sheet_name}")
        
        # Read the entire first sheet
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{first_sheet_name}'!A:Z").execute()
        return {"status": "success", "values": result.get('values', []), "range_used": first_sheet_name}
        
    except Exception as e:
        print(f"[ERROR] read_spreadsheet: {e}")
        return {"status": "error", "message": str(e)}

async def update_spreadsheet_values(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'sheets', 'v4')
    if not service: return {"error": "Google Sheets not connected"}
    body = {'values': parameters.get("values", [])}
    service.spreadsheets().values().update(spreadsheetId=parameters.get("spreadsheet_id"), range=parameters.get("range"), valueInputOption="RAW", body=body).execute()
    return {"status": "success"}

async def clear_spreadsheet_values(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'sheets', 'v4')
    if not service: return {"error": "Google Sheets not connected"}
    service.spreadsheets().values().clear(spreadsheetId=parameters.get("spreadsheet_id"), range=parameters.get("range")).execute()
    return {"status": "success"}
