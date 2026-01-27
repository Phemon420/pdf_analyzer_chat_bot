from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from models import get_db
from services import google_services
import io

router = APIRouter(prefix="/api/drive", tags=["drive"])

@router.get("/view/{file_id}")
async def view_drive_file(file_id: str, db: Session = Depends(get_db)):
    """Proxy endpoint to stream a PDF file from Google Drive to the frontend."""
    user_id = 1  # Default for now
    service = google_services.get_service(db, user_id, 'drive', 'v3')
    if not service:
        raise HTTPException(status_code=400, detail="Google Drive not connected")
    
    try:
        # Get metadata to verify it's a PDF and get the filename
        file_metadata = service.files().get(fileId=file_id, fields="name, mimeType").execute()
        if file_metadata.get("mimeType") != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF files can be viewed via this proxy")
        
        # Download the file content
        request = service.files().get_media(fileId=file_id)
        content = request.execute()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{file_metadata.get('name')}\""
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
