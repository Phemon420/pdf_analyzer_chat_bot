from sqlalchemy.orm import Session

from agents.auth import get_service


async def list_drive_files(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'drive', 'v3')
        if not service: return {"error": "Google Drive not connected"}
        
        query_parts = []
        filename = parameters.get("filename")
        if filename:
            safe_filename = filename.replace("'", "\\'")
            query_parts.append(f"name contains '{safe_filename}'")
            
        mime_type = parameters.get("mime_type")
        if mime_type:
            query_parts.append(f"mimeType = '{mime_type}'")
            
        raw_query = parameters.get("query")
        if raw_query:
            raw_query = raw_query.replace("title ", "name ").replace("title=", "name=")
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
    except Exception as e:
        error_msg = str(e)
        if "10060" in error_msg:
            error_msg = "Network Timeout (10060): Google server did not respond. Please check your internet connection, Firewall, or VPN settings."
        print(f"[DRIVE ERROR] {error_msg}")
        return {"status": "error", "message": error_msg}

async def upload_to_drive(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'drive', 'v3')
        if not service: return {"error": "Google Drive not connected"}
        from googleapiclient.http import MediaByteArrayUpload
        media = MediaByteArrayUpload(parameters.get('content', '').encode(), mime_type='text/plain')
        file = service.files().create(body={'name': parameters.get('filename')}, media_body=media).execute()
        return {"status": "success", "file_id": file.get('id')}
    except Exception as e:
        print(f"[DRIVE ERROR] {e}")
        return {"status": "error", "message": str(e)}

async def update_drive_file(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'drive', 'v3')
        if not service: return {"error": "Google Drive not connected"}
        updated = service.files().update(fileId=parameters.get("file_id"), body={'name': parameters.get('filename')}).execute()
        return {"status": "success", "file_id": updated.get('id')}
    except Exception as e:
        print(f"[DRIVE ERROR] {e}")
        return {"status": "error", "message": str(e)}

async def delete_drive_file(db: Session, user_id: int, parameters: dict) -> dict:
    try:
        service = get_service(db, user_id, 'drive', 'v3')
        if not service: return {"error": "Google Drive not connected"}
        service.files().delete(fileId=parameters.get("file_id")).execute()
        return {"status": "success", "message": "File deleted"}
    except Exception as e:
        print(f"[DRIVE ERROR] {e}")
        return {"status": "error", "message": str(e)}

async def read_drive_file_content(db: Session, user_id: int, parameters: dict) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    file_id = parameters.get("file_id")
    try:
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        mime_type = file_metadata.get("mimeType")

        if mime_type == "application/vnd.google-apps.document":
            content = service.files().export(fileId=file_id, mimeType='text/plain').execute()
            return {"status": "success", "content": content.decode('utf-8'), "name": file_metadata.get("name")}
        elif mime_type.startswith("text/"):
            content = service.files().get_media(fileId=file_id).execute()
            return {"status": "success", "content": content.decode('utf-8'), "name": file_metadata.get("name")}
        elif mime_type == "application/pdf":
            return await read_drive_pdf_content(db, user_id, file_id, file_metadata.get("name"))
        else:
            return {"status": "error", "message": f"Reading content of type '{mime_type}' is not yet supported directly. Only Google Docs, PDFs, and text files can be read."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def read_drive_pdf_content(db: Session, user_id: int, file_id: str, file_name: str) -> dict:
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}

    try:
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

        content = service.files().export(
            fileId=temp_doc_id,
            mimeType='text/plain'
        ).execute()

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
    service = get_service(db, user_id, 'drive', 'v3')
    if not service: return {"error": "Google Drive not connected"}
    try:
        file = service.files().get(fileId=file_id, fields='webViewLink, webContentLink').execute()
        return {"status": "success", "link": file.get('webViewLink')}
    except Exception as e:
        return {"status": "error", "message": str(e)}
