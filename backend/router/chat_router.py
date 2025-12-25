from package import *
from controller.chat_controller import *


@router.post("/chat/pdf/stream")
async def chat_endpoint(
    request: Request,
    message: str = Form(...),
    file: UploadFile = File(None),
    session_id: str = Form(None),
):
    active_session_id = session_id or str(uuid.uuid4())
    redis_client = request.app.state.redis_client
    # 1. Try to load existing session data from Redis
    raw_data = await redis_client.get(f"chat:{active_session_id}")
    session_data = json.loads(raw_data) if raw_data else {"messages": [], "source_map": {}, "pdf_filename": ""}
    
    history = session_data.get("messages", [])
    source_map = session_data.get("source_map", {})
    pdf_filename = session_data.get("pdf_filename", "Document")

    # 2. If a new PDF is uploaded, override the context
    if file:
        pdf_bytes = await file.read()
        pdf_filename = file.filename
        context_text, source_map = prepare_context_and_metadata(pdf_bytes)
        
        system_content = f"You are a PDF assistant. Cite as [ID]. Context:\n{context_text}"
        # Inject context as the first message
        history = [{"role": "system", "content": system_content}]

    # 3. Add current user message
    history.append({"role": "user", "content": message})

    # 4. Stream the Response
    return StreamingResponse(
        dynamic_pdf_stream_with_redis(
            gemini_client=request.app.state.client_gemini,
            messages=history,
            session_id=active_session_id,
            redis_client=redis_client,
            source_map=source_map, # This ensures citations work
            pdf_filename=pdf_filename
        ),
        media_type="text/event-stream"
    )