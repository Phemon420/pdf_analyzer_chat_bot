from package import *


def prepare_context_and_metadata(pdf_bytes):
    pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_bytes))
    context_chunks = []
    source_map = {}

    for i, page in enumerate(pdf_reader.pages):
        page_num = i + 1
        text = page.extract_text() or ""
        source_id = page_num 
        
        context_chunks.append(f"--- SOURCE ID: {source_id}, PAGE: {page_num} ---\n{text}\n")
        # Store metadata for citation mapping
        source_map[str(source_id)] = {
            "id": source_id,
            "page": page_num,
            "snippet": text[:150] + "..."
        }
        
    return "".join(context_chunks), source_map

async def dynamic_pdf_stream_db(
    gemini_client, 
    messages, 
    session_id, 
    user_id, 
    source_map, 
    pdf_filename
):
    db = SessionLocal()
    try:
        full_text = ""
        # 1. UI Initial Step
        yield f"data: {json.dumps({'type': 'analysing-pdf', 'message': 'Checking document and history...'})}\n\n"

        # 2. Start Gemini Stream
        print(f"[LOGGER] PDF CHAT ({session_id}) REQUEST: {messages[-1]['content']}")
        response = gemini_client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=messages,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_text += content
                yield f"data: {json.dumps({'type': 'ai-response', 'chunk': content})}\n\n"
                await asyncio.sleep(0)

        print(f"[LOGGER] PDF CHAT ({session_id}) RESPONSE: {full_text[:200]}...")

        # 3. DYNAMIC CITATION MAPPING
        found_ids = list(set(re.findall(r'\[(\d+)\]', full_text)))
        dynamic_citations = []
        for sid in found_ids:
            if sid in source_map:
                meta = source_map[sid]
                dynamic_citations.append({
                    "id": int(sid),
                    "file_name": pdf_filename,
                    "page": meta["page"],
                    "snippet": meta["snippet"]
                })

        if dynamic_citations:
            yield f"data: {json.dumps({'type': 'sources', 'citations': dynamic_citations})}\n\n"

        # 4. SAVE TO DB
        assistant_msg = ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=full_text,
            citations=dynamic_citations if dynamic_citations else None
        )
        db.add(assistant_msg)
        db.commit()

        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    except Exception as e:
        print(f"[ERROR] PDF Stream Error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    finally:
        db.close()