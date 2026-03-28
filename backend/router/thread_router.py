from package import *
from controller.thread_store import (
    create_thread, get_thread, list_threads,
    get_messages, delete_thread
)
from fastapi import responses


@router.get("/threads")
async def get_all_threads(request: Request):
    return {"status": 1, "threads": list_threads()}


@router.post("/threads")
async def create_new_thread(request: Request):
    thread = create_thread()
    return {"status": 1, "thread": thread}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request):
    thread = get_thread(thread_id)
    if not thread:
        return responses.JSONResponse(status_code=404, content={"status": 0, "message": "Thread not found"})

    messages = get_messages(thread_id)
    formatted = [
        {
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "createdAt": m["created_at"],
            "toolName": m.get("tool_name"),
        }
        for m in messages
    ]
    return {"status": 1, "messages": formatted}


@router.delete("/threads/{thread_id}")
async def delete_existing_thread(thread_id: str, request: Request):
    success = delete_thread(thread_id)
    if not success:
        return responses.JSONResponse(status_code=404, content={"status": 0, "message": "Thread not found"})
    return {"status": 1, "message": "Thread deleted"}
