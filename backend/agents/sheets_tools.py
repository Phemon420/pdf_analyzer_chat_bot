from sqlalchemy.orm import Session

from agents.auth import get_service


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

        if user_range:
            try:
                result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=user_range).execute()
                return {"status": "success", "values": result.get('values', [])}
            except Exception as e:
                print(f"[RECOVERABLE ERROR] Failed to read specific range '{user_range}': {e}. Falling back to first sheet.")

        spread_meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = spread_meta.get('sheets', [])
        if not sheets:
            return {"error": "No sheets found in spreadsheet"}

        first_sheet_name = sheets[0].get('properties', {}).get('title', 'Sheet1')
        print(f"[LOGGER] Defaulting to first sheet: {first_sheet_name}")

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
