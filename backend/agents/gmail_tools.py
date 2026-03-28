import base64
from email.mime.text import MIMEText
from sqlalchemy.orm import Session

from agents.auth import get_service


async def send_email(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'gmail', 'v1')
        if not service: return {"error": "Gmail not connected"}
        
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
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[GMAIL ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def read_emails(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'gmail', 'v1')
        if not service: return {"error": "Gmail not connected"}
        results = service.users().messages().list(userId='me', q=parameters.get("query", ""), maxResults=parameters.get("max_results", 10)).execute()
        emails = []
        for msg in results.get('messages', []):
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = {h['name']: h['value'] for h in m.get('payload', {}).get('headers', [])}
            emails.append({"id": msg['id'], "subject": headers.get('Subject'), "from": headers.get('From'), "snippet": m.get('snippet')})
        return {"status": "success", "emails": emails}
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[GMAIL ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def delete_email(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'gmail', 'v1')
        if not service: return {"error": "Gmail not connected"}
        service.users().messages().trash(userId='me', id=parameters.get("message_id")).execute()
        return {"status": "success", "message": "Email moved to trash"}
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[GMAIL ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def update_email_labels(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'gmail', 'v1')
        if not service: return {"error": "Gmail not connected"}
        body = {
            "addLabelIds": parameters.get("add_labels", []),
            "removeLabelIds": parameters.get("remove_labels", [])
        }
        service.users().messages().modify(userId='me', id=parameters.get("message_id"), body=body).execute()
        return {"status": "success"}
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[GMAIL ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}
