import json
import os
from typing import Optional, List, Dict, Any
from mcp.server.fastmcp import FastMCP
from models import SessionLocal
from services import google_services

# Initialize FastMCP Server
mcp = FastMCP("GoogleWorkspaceTools")

USER_ID = 1  # Default user ID for execution context

# --- CALENDAR TOOLS ---

@mcp.tool()
async def check_calendar_availability(user_id: int, days: int) -> str:
    """Check Google Calendar availability for the next X days. Returns busy slots. Use this when the user asks for free time or availability."""
    db = SessionLocal()
    try:
        result = await google_services.check_calendar_availability(db, user_id, {"days": days})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def schedule_calendar_event(user_id: int, start_time: str, end_time: str, title: str, attendee_email: Optional[str] = None, description: Optional[str] = None) -> str:
    """Schedule a new event on Google Calendar. Use this to create a new appointment or event."""
    db = SessionLocal()
    try:
        result = await google_services.schedule_calendar_event(db, user_id, {
            "start_time": start_time,
            "end_time": end_time,
            "title": title,
            "attendee_email": attendee_email,
            "description": description
        })
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def update_calendar_event(user_id: int, event_id: str, title: Optional[str] = None, start_time: Optional[str] = None, end_time: Optional[str] = None, description: Optional[str] = None) -> str:
    """Update an existing Google Calendar event. Use this to modify an existing calendar event."""
    db = SessionLocal()
    try:
        result = await google_services.update_calendar_event(db, user_id, {
            "event_id": event_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "description": description
        })
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def delete_calendar_event(user_id: int, event_id: str) -> str:
    """Delete an event from Google Calendar. Use this to remove a scheduled event."""
    db = SessionLocal()
    try:
        result = await google_services.delete_calendar_event(db, user_id, {"event_id": event_id})
        return json.dumps(result)
    finally:
        db.close()


# --- GMAIL TOOLS ---

@mcp.tool()
async def send_email(user_id: int, to_email: str, subject: str, body: str) -> str:
    """Send an email via Gmail. Use this to send a message to one or more people via email. Supports a single email string or a list of emails."""
    db = SessionLocal()
    try:
        result = await google_services.send_email(db, user_id, {"to_email": to_email, "subject": subject, "body": body})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def read_emails(user_id: int, query: Optional[str] = None, max_results: Optional[int] = 10) -> str:
    """List recent emails from Gmail inbox with snippets. Use this to check the inbox or find specific emails."""
    db = SessionLocal()
    try:
        result = await google_services.read_emails(db, user_id, {"query": query, "max_results": max_results})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def delete_email(user_id: int, message_id: str) -> str:
    """Move a Gmail message to the trash. Use this to delete an unwanted email."""
    db = SessionLocal()
    try:
        result = await google_services.delete_email(db, user_id, {"message_id": message_id})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def update_email_labels(user_id: int, message_id: str, add_labels: Optional[List[str]] = None, remove_labels: Optional[List[str]] = None) -> str:
    """Add or remove labels from a Gmail message. Use this to organize emails into folders/labels."""
    db = SessionLocal()
    try:
        result = await google_services.update_email_labels(db, user_id, {"message_id": message_id, "add_labels": add_labels, "remove_labels": remove_labels})
        return json.dumps(result)
    finally:
        db.close()


# --- DRIVE TOOLS ---

@mcp.tool()
async def list_drive_files(user_id: int, page_size: Optional[int] = 10, query: Optional[str] = None, filename: Optional[str] = None, mime_type: Optional[str] = None) -> str:
    """List files from Google Drive. Highly recommended to use 'filename' or 'mime_type' for precise searching. Use this to see files or search for a document. Prefer 'filename' for exact matches."""
    db = SessionLocal()
    try:
        result = await google_services.list_drive_files(db, user_id, {"page_size": page_size, "query": query, "filename": filename, "mime_type": mime_type})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def upload_to_drive(user_id: int, filename: str, content: str) -> str:
    """Upload content to a new text file on Google Drive. Use this to save text data or create a new file."""
    db = SessionLocal()
    try:
        result = await google_services.upload_to_drive(db, user_id, {"filename": filename, "content": content})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def update_drive_file(user_id: int, file_id: str, filename: str) -> str:
    """Update the name of an existing Google Drive file. Use this to rename a file."""
    db = SessionLocal()
    try:
        result = await google_services.update_drive_file(db, user_id, {"file_id": file_id, "filename": filename})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def delete_drive_file(user_id: int, file_id: str) -> str:
    """Permanently delete a file from Google Drive. Use this to remove a file from Drive."""
    db = SessionLocal()
    try:
        result = await google_services.delete_drive_file(db, user_id, {"file_id": file_id})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def read_drive_file_content(user_id: int, file_id: str) -> str:
    """Read the content of a Google Drive file. Supports Google Docs (exports to text) and text files. Use this to read the text inside a document or file."""
    db = SessionLocal()
    try:
        result = await google_services.read_drive_file_content(db, user_id, {"file_id": file_id})
        return json.dumps(result)
    finally:
        db.close()


# --- SHEETS TOOLS ---

@mcp.tool()
async def create_spreadsheet(user_id: int, title: str) -> str:
    """Create a new Google Sheets spreadsheet. Use this to start a new spreadsheet."""
    db = SessionLocal()
    try:
        result = await google_services.create_spreadsheet(db, user_id, {"title": title})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def read_spreadsheet(user_id: int, spreadsheet_id: str, range: Optional[str] = None) -> str:
    """Read values from a Google Sheets range. Use this to fetch data from a sheet. Leave 'range' empty to automatically read the first sheet unless a specific tab name is known."""
    db = SessionLocal()
    try:
        result = await google_services.read_spreadsheet(db, user_id, {"spreadsheet_id": spreadsheet_id, "range": range})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def update_spreadsheet_values(user_id: int, spreadsheet_id: str, range: str, values: List[List[Any]]) -> str:
    """Overwrite a range of values in Google Sheets. Use this to update or edit spreadsheet data."""
    db = SessionLocal()
    try:
        result = await google_services.update_spreadsheet_values(db, user_id, {"spreadsheet_id": spreadsheet_id, "range": range, "values": values})
        return json.dumps(result)
    finally:
        db.close()

@mcp.tool()
async def clear_spreadsheet_values(user_id: int, spreadsheet_id: str, range: str) -> str:
    """Clear all values in a specified Google Sheets range. Use this to wipe data from a section of a sheet."""
    db = SessionLocal()
    try:
        result = await google_services.clear_spreadsheet_values(db, user_id, {"spreadsheet_id": spreadsheet_id, "range": range})
        return json.dumps(result)
    finally:
        db.close()


@mcp.tool()
async def get_current_time(user_id: int, timezone: str = "Asia/Kolkata") -> str:
    """Get the current date and time for a specific timezone using World Time API. Use this when the user asks for the current time or date or when scheduling events."""
    import httpx
    api_key = os.getenv("timezone_api_key")
    if not api_key:
        return json.dumps({"status": "error", "message": "API key 'timezone_api_key' not found in environment"})
        
    url = f"https://world-time-api3.p.rapidapi.com/timezone/{timezone}"
    headers = {
        "x-api-host": "world-time-api3.p.rapidapi.com",
        "x-api-key": api_key
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                # The API returns a multiline string in the user's example, 
                # but if it's JSON we parse it.
                try:
                    return json.dumps(response.json())
                except:
                    return response.text
            else:
                return json.dumps({"status": "error", "message": f"API returned status {response.status_code}: {response.text}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    mcp.run()
