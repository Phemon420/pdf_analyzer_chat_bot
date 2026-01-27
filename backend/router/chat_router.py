from package import *
from controller.chat_controller import *
from fastapi import responses
from sqlalchemy import func, text


@router.get("/chat/history")
async def get_chat_history(request: Request):
    """List all unique chat sessions for the user."""
    user = request.state.user
    if user is None:
        return responses.JSONResponse(status_code=401, content={"status": 0, "message": "Authentication required"})
    
    db = SessionLocal()
    try:
        # Get unique session IDs and their latest message for title/timestamp
        sessions_query = db.query(
            ChatMessage.session_id,
            func.max(ChatMessage.created_at).label("updatedAt"),
            func.min(ChatMessage.content).label("title") # Simple title strategy: first message
        ).filter(ChatMessage.user_id == user["id"]).group_by(ChatMessage.session_id).order_by(text("updatedAt DESC")).all()
        
        sessions = []
        for s in sessions_query:
            sessions.append({
                "id": s.session_id,
                "title": s.title[:50] + "..." if s.title else "New Chat",
                "updatedAt": s.updatedAt.isoformat()
            })
        
        return {"status": 1, "sessions": sessions}
    finally:
        db.close()

@router.get("/chat/history/{session_id}")
async def get_session_history(session_id: str, request: Request):
    """Fetch all messages for a specific session."""
    user = request.state.user
    if user is None:
        return responses.JSONResponse(status_code=401, content={"status": 0, "message": "Authentication required"})
    
    db = SessionLocal()
    try:
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.user_id == user["id"]
        ).order_by(ChatMessage.created_at.asc()).all()
        
        return {"status": 1, "messages": [m.to_dict() for m in messages]}
    finally:
        db.close()

@router.post("/chat/pdf/stream")
async def chat_endpoint(
    request: Request,
    message: str = Form(...),
    file: UploadFile = File(None),
    session_id: str = Form(None),
):
    active_session_id = session_id or str(uuid.uuid4())
    user = request.state.user
    user_id = user.get("id") if user else None
    
    if user_id is None:
        return responses.JSONResponse(status_code=401, content={"status": 0, "message": "Authentication required"})
    
    db = SessionLocal()
    history = []
    source_map = {}
    pdf_filename = "Document"

    try:
        # 1. Load existing history from DB
        existing_msgs = db.query(ChatMessage).filter(
            ChatMessage.session_id == active_session_id
        ).order_by(ChatMessage.created_at.asc()).all()
        
        for m in existing_msgs:
            history.append({"role": m.role, "content": m.content})
            if m.citations and not source_map: # Use citations from first assistant message with citations
                # This is a bit simplistic, but we primarily need citations for the CURRENT pdf
                pass

        # 2. If a new PDF is uploaded, override the context
        if file:
            pdf_bytes = await file.read()
            pdf_filename = file.filename
            context_text, source_map = prepare_context_and_metadata(pdf_bytes)
            
            system_content = f"You are a PDF assistant. Cite as [ID]. Context:\n{context_text}"
            # Inject context or append
            history.insert(0, {"role": "system", "content": system_content})

        # 3. Add current user message
        history.append({"role": "user", "content": message})
        
        # Save user message to DB
        user_msg = ChatMessage(
            session_id=active_session_id,
            user_id=user_id,
            role="user",
            content=message
        )
        db.add(user_msg)
        db.commit()

        # 4. Stream the Response
        return StreamingResponse(
            dynamic_pdf_stream_db(
                gemini_client=request.app.state.client_gemini,
                messages=history,
                session_id=active_session_id,
                user_id=user_id,
                source_map=source_map,
                pdf_filename=pdf_filename
            ),
            media_type="text/event-stream"
        )
    finally:
        db.close()