from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from agents.auth import get_service


async def check_calendar_availability(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        days = int(parameters.get("days", 7))
        service = get_service(db, user_id, 'calendar', 'v3')
        if not service: return {"error": "Google Calendar not connected"}
        
        # IST Context: Query should start from 'now'
        now = datetime.now(timezone.utc)
        
        # If days is 0, query until the end of the current day (IST context)
        if days == 0:
            time_max = now + timedelta(hours=24)
        else:
            time_max = now + timedelta(days=days)
            
        print(f"[GOOGLE CALENDAR] Listing events from {now.isoformat()} to {time_max.isoformat()}")
        
        # Switching from FreeBusy to Events.list to get Titles/Summaries
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        simplified_events = []
        for event in events:
            simplified_events.append({
                "title": event.get('summary', 'No Title'),
                "start": event.get('start', {}).get('dateTime', event.get('start', {}).get('date')),
                "end": event.get('end', {}).get('dateTime', event.get('end', {}).get('date')),
                "id": event.get('id')
            })
            
        return {"status": "success", "events": simplified_events}
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[CALENDAR ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def schedule_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    try:
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
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[CALENDAR ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def update_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'calendar', 'v3')
        if not service: return {"error": "Google Calendar not connected"}
        event_id = parameters.get("event_id")
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if parameters.get('title'): event['summary'] = parameters.get('title')
        if parameters.get('start_time'): event['start'] = {'dateTime': parameters.get('start_time'), 'timeZone': 'UTC'}
        if parameters.get('end_time'): event['end'] = {'dateTime': parameters.get('end_time'), 'timeZone': 'UTC'}
        updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        return {"status": "success", "event_id": updated_event.get('id')}
    except Exception as e:
        print(f"[CALENDAR ERROR] {e}")
        return {"status": "error", "message": str(e)}

async def delete_calendar_event(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'calendar', 'v3')
        if not service: return {"error": "Google Calendar not connected"}
        service.events().delete(calendarId='primary', eventId=parameters.get("event_id")).execute()
        return {"status": "success", "message": "Event deleted"}
    except Exception as e:
        print(f"[CALENDAR ERROR] {e}")
        return {"status": "error", "message": str(e)}
