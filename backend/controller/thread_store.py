import time
import uuid
from typing import Dict, List, Any, Optional

thread_counter = {"count": 0}
threads: Dict[str, Dict[str, Any]] = {}

def create_thread() -> Dict[str, Any]:
    thread_counter["count"] += 1
    thread_id = str(uuid.uuid4())
    thread_name = f"thread{thread_counter['count']}"
    thread = {
        "id": thread_id,
        "name": thread_name,
        "messages": [],
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    threads[thread_id] = thread
    return thread

def get_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    return threads.get(thread_id)

def get_or_create_thread(thread_id: Optional[str] = None) -> Dict[str, Any]:
    if thread_id and thread_id in threads:
        return threads[thread_id]
    return create_thread()

def list_threads() -> List[Dict[str, Any]]:
    sorted_threads = sorted(threads.values(), key=lambda t: t["updated_at"], reverse=True)
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "title": t["messages"][0]["content"][:50] + "..." if t["messages"] and t["messages"][0]["content"] else t["name"],
            "updated_at": t["updated_at"],
            "message_count": len(t["messages"]),
        }
        for t in sorted_threads
    ]

def add_message(thread_id: str, role: str, content: str, tool_name: str = None, extra: Dict = None) -> Dict[str, Any]:
    thread = threads.get(thread_id)
    if not thread:
        return None
    msg = {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content or "",
        "tool_name": tool_name,
        "created_at": time.time(),
    }
    if extra:
        msg.update(extra)
    thread["messages"].append(msg)
    thread["updated_at"] = time.time()
    return msg

def get_messages(thread_id: str) -> List[Dict[str, Any]]:
    thread = threads.get(thread_id)
    if not thread:
        return []
    return thread["messages"]

def get_openai_history(thread_id: str, limit: int = 20) -> List[Dict[str, str]]:
    thread = threads.get(thread_id)
    if not thread:
        return []
    history = []
    for m in thread["messages"]:
        if m["role"] == "tool":
            history.append({"role": "system", "content": f"Output from tool '{m.get('tool_name', 'unknown')}': {m['content']}"})
        elif m["role"] in ("user", "assistant", "system"):
            history.append({"role": m["role"], "content": m["content"]})
    if len(history) > limit:
        history = history[-limit:]
    return history

def delete_thread(thread_id: str) -> bool:
    if thread_id in threads:
        del threads[thread_id]
        return True
    return False

def clear_all_threads():
    threads.clear()
    thread_counter["count"] = 0
