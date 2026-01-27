from package import *
import json
import time
import asyncio
import traceback
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from models import SessionLocal, ChatMessage
from services import google_services
from fastapi import WebSocketDisconnect

# --- CONSTANTS ---
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 10   # seconds

async def safe_send(websocket, data: dict) -> bool:
    """Safely send data via WebSocket, return False if connection is closed.
    
    This prevents RuntimeError when trying to send after the connection is closed.
    """
    try:
        await websocket.send_text(json.dumps(data))
        return True
    except (WebSocketDisconnect, RuntimeError) as e:
        print(f"[WS SAFE_SEND] Connection closed, cannot send: {type(e).__name__}")
        return False
    except Exception as e:
        print(f"[WS SAFE_SEND] Unexpected error: {e}")
        return False

# Load tool registry
TOOLS_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools.json")

def load_tools_registry() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(TOOLS_REGISTRY_PATH):
            with open(TOOLS_REGISTRY_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading tools registry: {e}")
    return []

TOOLS_REGISTRY = load_tools_registry()

# Local memory cache for workflow state
local_workflow_cache = {}

class WorkflowState:
    """Manages workflow state for a session with Database and Local Cache"""
    
    def __init__(self, session_id: str, db: Session, user_id: int):
        self.session_id = session_id
        self.db = db
        self.user_id = user_id
    
    async def load(self) -> Dict[str, Any]:
        """Load workflow state from Local Cache"""
        if self.session_id in local_workflow_cache:
            return local_workflow_cache[self.session_id]
            
        return {
            "workflow_id": None,
            "status": "active",
            "history": [],
            "previous_response_id": None,
            "pending_tool": None,  # { name, arguments, hitl_type }
            "current_step": 0,
            "user_goal": None,
            "execution_context": {},  # Context passed between steps
            "plan": None
        }
    
    async def save(self, state: Dict[str, Any]):
        """Save workflow state to Local Cache"""
        if len(state.get("history", [])) > 20:
            state["history"] = state["history"][-20:]
        
        local_workflow_cache[self.session_id] = state

    async def save_message(self, role: str, content: str = None, tool_name: str = None, hitl_type: str = None, hitl_schema: Dict = None, workflow_state: Dict = None):
        """Persist message to database and update cache"""
        msg = ChatMessage(
            session_id=self.session_id,
            user_id=self.user_id,
            role=role,
            content=content,
            tool_name=tool_name,
            hitl_type=hitl_type,
            hitl_schema=hitl_schema
        )
        self.db.add(msg)
        self.db.commit()
        
        if workflow_state:
            await self.save(workflow_state)

    async def get_full_history(self) -> List[Dict]:
        """Retrieve chat history for the current session from database"""
        messages = self.db.query(ChatMessage).filter(ChatMessage.session_id == self.session_id).order_by(ChatMessage.created_at.asc()).all()
        history = []
        for m in messages:
            if m.role == "tool":
                # OpenAI gpt-4o requires tool role messages to follow assistant tool_calls.
                # Since we execute manually, we'll map these to 'system' role for context.
                msg = {"role": "system", "content": f"Output from tool '{m.tool_name}': {m.content}"}
            else:
                msg = {"role": m.role, "content": m.content}
            history.append(msg)
        return history

# --- STRUCTURED OUTPUT SCHEMA ---
FORMAT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "structured_article",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "pqa": {
                    "type": "array",
                    "description": "Variable number of questions and answers for parents to help their children",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "question": {"type": "string", "description": "Question for parents"},
                            "answer": {"type": "string", "description": "Answer to the question"}
                        },
                        "required": ["question", "answer"]
                    }
                },
                "paragraphs": {
                    "type": "array",
                    "description": "Variable number of middle paragraphs expanding on the topic",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "content": {"type": "string", "description": "Main content of the paragraph"},
                            "math_formula": {"type": "string", "description": "Optional LaTeX formatted math formula associated with the paragraph"}
                        },
                        "required": ["content", "math_formula"]
                    }
                },
                "accordion": {
                    "type": "array",
                    "description": "Variable number of middle pre-requisites for the topic",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "heading": {"type": "string", "description": "heading for this concept"},
                            "content": {"type": "string", "description": "short explanation of the heading"},
                            "hyper-link": {"type": "string", "description": "only show these words 'learn more'."}
                        },
                        "required": ["heading", "content", "hyper-link"]
                    }
                },
                "pop_up": {
                    "type": "array",
                    "description": "Variable number of additional resources for further learning",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "title": {"type": "string", "description": "Title of the resource"},
                            "description": {"type": "string", "description": "Brief description of the resource"}
                        },
                        "required": ["title", "description"]
                    }
                },
                "end_toggle": {
                    "type": "object",
                    "description": "this is an closing paragraph which will tell the user that they have completed the topic successfully it will be wrapped inside accordion",
                    "additionalProperties": False,
                    "properties": {
                        "heading": {
                            "type": "string",
                            "description": "heading for the toggle section should be exactly these words 'next steps to learning'"
                        },
                        "content": {
                            "type": "string",
                            "description": "starting content of the toggle section"
                        },
                        "buttons": {
                            "type": "array",
                            "description": "Variable number of middle pre-requisites for the topic",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "heading": {"type": "string", "description": "heading for this concept"},
                                    "content": {"type": "string", "description": "short explanation of the heading"}
                                },
                                "required": ["heading", "content"]
                            }
                        }
                    },
                    "required": ["heading", "content", "buttons"]
                }
            },
            "required": ["pqa", "paragraphs", "pop_up", "accordion", "end_toggle"]
        }
    }
}

async def extract_variables(client_openai, user_message: str) -> Dict[str, Any]:
    """Pre-extract potential tool parameters from the user message with improved mapping."""
    prompt = f"""
    Extract any relevant entities or variables from the user query that might be useful for tools (Google Calendar, Gmail, Google Drive, Sheets).
    Extract things like: email addresses, event titles, dates, times, file names, spreadsheet names, content, etc.
    
    User Query: "{user_message}"
    
    Return a JSON object with the extracted variables. Map them to the exact parameter names used by tools:
    {{
      "to_email": "extracted email address if present",
      "subject": "email subject if mentioned",
      "body": "email body/content if mentioned",
      "title": "event or file title if present",
      "start_time": "ISO datetime if mentioned (e.g., 2024-01-26T10:00:00)",
      "end_time": "ISO datetime if mentioned",
      "days": "number of days if mentioned",
      "filename": "file name if mentioned",
      "content": "content/text to be used",
      "attendee_email": "attendee email if mentioned",
      "description": "description if mentioned",
      "query": "search query if mentioned"
    }}
    
    Only include fields that have actual values extracted. Use null for fields without values.
    """
    response = await client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a helpful data extractor. Extract parameters accurately."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    extracted = json.loads(response.choices[0].message.content)
    # Remove null values
    return {k: v for k, v in extracted.items() if v is not None and v != ""}

async def plan_workflow(client_openai, user_message: str, tools_registry: List[Dict], extracted_vars: Dict[str, Any] = None) -> List[Dict]:
    """Decide the order of tools and extract initial variables with proper execution sequence."""
    tools_info = []
    for tool in tools_registry:
        tools_info.append({
            "tool_id": tool["tool_id"],
            "description": tool["tool_description"],
            "required_params": tool["must_required_params"],
            "optional_params": tool.get("optional_params", []),
            "when_to_use": tool.get("exact_precise_tool_use", "")
        })
    
    prompt = f"""
    Analyze the user query and available tools to create an execution plan.
    User Query: "{user_message}"
    Available Tools: {json.dumps(tools_info, indent=2)}
    Extracted Variables: {json.dumps(extracted_vars or {}, indent=2)}
    
    IMPORTANT: You MUST ONLY use the tools provided in the 'Available Tools' list. Do not imagine or hallucinate tools that are not listed.
    If the user's request requires a tool that is not available, include only the available steps and explain the limitation in the summary.
    
    Create a step-by-step execution plan that:
    1. Orders tools in the correct sequence (dependencies first)
    2. Maps extracted variables to the correct tool parameters
    3. Identifies which parameters need to be collected from the user
    4. Specifies how results from one step feed into the next
    
    Return a JSON object with a "plan" array:
    {{
      "plan": [
        {{
          "step": 1,
          "tool_id": "tool_name",
          "variables": {{ "param1": "value_from_extracted_or_previous_step" }},
          "missing_variables": ["param2"],
          "description": "What this step accomplishes",
          "depends_on_step": null,
          "output_used_by": [2]
        }}
      ],
      "summary": "Brief overview of the entire workflow"
    }}
    """
    response = await client_openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a professional workflow architect. You create structured, efficient plans for complex tasks."},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    plan_data = json.loads(response.choices[0].message.content)
    return plan_data.get("plan", plan_data.get("calls", []))

async def verify_step_result(client_openai, tool_name: str, tool_args: Dict, tool_result: Dict, 
                              user_goal: str, remaining_plan: List[Dict], execution_context: Dict) -> Dict[str, Any]:
    """LLM verification of tool execution result with context for next step."""
    prompt = f"""
    Verify the result of tool execution and provide context for next steps.
    
    User Goal: {user_goal}
    Tool Executed: {tool_name}
    Arguments Used: {json.dumps(tool_args)}
    Result: {json.dumps(tool_result)}
    Previous Context: {json.dumps(execution_context)}
    Remaining Steps: {json.dumps(remaining_plan)}
    
    Analyze the result and respond with JSON:
    {{
        "success": true/false (did the tool execute successfully?),
        "summary": "Brief summary of what happened",
        "context_for_next_step": {{ "key": "value" }} (extracted data for next tools),
        "should_continue": true/false (should we proceed with the plan?),
        "updated_variables": {{ "param": "value" }} (variables to update for next steps),
        "error_recovery": "suggestion if there was an error",
        "reason": "Explanation of the decision"
    }}
    """
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI validation agent. Your job is to verify tool outputs and ensure the workflow stays on track."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[VERIFICATION ERROR] {e}")
        return {
            "success": tool_result.get("status") != "error",
            "summary": "Verification skipped due to error",
            "context_for_next_step": {},
            "should_continue": True,
            "updated_variables": {},
            "reason": str(e)
        }

async def find_similar_files(client_openai, search_query: str, available_files: List[Dict], user_goal: str = "") -> Dict[str, Any]:
    """Use LLM to find files similar to the user's search query from available files with strict validation."""
    if not available_files:
        return {"matches": [], "message": "No files available in Drive"}
    
    # Prepare file list for LLM
    files_summary = []
    for f in available_files[:100]:  # Limit to 100 files
        files_summary.append({
            "id": f.get("id"),
            "name": f.get("name"),
            "mimeType": f.get("mimeType", "unknown")
        })
    
    prompt = f"""
    The user is performing a search in Google Drive.
    User's Original Goal: "{user_goal}"
    Active Search Query: "{search_query}"
    
    Here are the available items (Files/Spreadsheets) in their Google Drive:
    {json.dumps(files_summary, indent=2)}
    
    TASK: Act as a strict validation layer. Identify only the items that are TRULY relevant to the user's search or goal.
    
    STRICT FILTERING RULES:
    1. If a file is completely unrelated (e.g., an mp4 when searching for a document), EXCLUDE IT.
    2. If a file has a generic name that doesn't match the context (e.g., "Untitled"), EXCLUDE IT unless it's the only match.
    3. Categorize matches into "High", "Medium", or "Low" relevance.
    4. Only return "High" and "Medium" matches.
    
    Return a JSON object with:
    {{
        "matches": [
            {{
                "id": "item_id",
                "name": "item_name",
                "mimeType": "mime_type",
                "relevance_score": 0.95,
                "relevance_label": "High",
                "reason": "Explicit reasoning why this satisfies the request"
            }}
        ],
        "best_match_id": "item_id_if_extremely_confident",
        "message": "Brief summary of the validation results"
    }}
    
    BEST MATCH CRITERIA:
    - Only populate "best_match_id" if there's exactly ONE perfect match (name matches exactly and type is correct).
    - If there's any ambiguity (multiple similar names), DO NOT set best_match_id, so the user can pick.
    - If the user specifically said "find me the content of [filename]", an exact match on that name is a Best Match.
    
    Order by relevance_score (highest first). Return max 10 matches.
    """
    
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional file retrieval and validation assistant. You are strict and do not return irrelevant results."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[SIMILARITY SEARCH ERROR] {e}")
        return {"matches": [], "message": f"Search failed: {str(e)}"}

async def resolve_step_parameters(client_openai, tool_name: str, user_goal: str, history: List[Dict], 
                                 context: Dict, step_def: Dict, tools_registry: List[Dict]) -> Dict[str, Any]:
    """
    Use LLM to resolve the most accurate parameters for the NEXT tool call
    based on the entire execution history and context.
    """
    tool_def = next((t for t in tools_registry if t["tool_id"] == tool_name), None)
    
    prompt = f"""
    The user wants to: "{user_goal}"
    
    We are about to execute the tool: "{tool_name}"
    Tool Description: {tool_def.get('tool_description') if tool_def else 'N/A'}
    Tool Required Params: {tool_def.get('must_required_params') if tool_def else '[]'}
    Tool Optional Params: {tool_def.get('optional_params') if tool_def else '[]'}
    
    Current Plan Step Definition:
    {json.dumps(step_def, indent=2)}
    
    Active Execution Context (Variables):
    {json.dumps(context, indent=2)}
    
    Full Execution History (Results from previous steps):
    {json.dumps(history[-10:], indent=2)}
    
    TASK: Determine the exact arguments to pass to the tool "{tool_name}".
    - Look into the Execution History to extract specific IDs (like file_id or message_id) if the plan refers to them.
    - Resolve any placeholders like "file_id_from_step_1" using the actual values from the history or context.
    - Ensure all REQUIRED parameters are present.
    
    Return ONLY a JSON object with the resolved arguments:
    {{
        "arguments": {{ "param1": "value1", "param2": "value2" }},
        "missing_params": ["list", "of", "params", "we", "still", "don't", "have"]
    }}
    """
    
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise parameters resolution engine. You extract values from history to satisfy tool requirements."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"[RESOLVE PARAMETERS ERROR] {e}")
        return {"arguments": step_def.get("variables", {}), "missing_params": step_def.get("missing_variables", [])}

def get_hitl_selection_schema(title: str, message: str, options: List[Dict], context: Dict = None) -> Dict[str, Any]:
    """Generate selection schema for single-choice file selection."""
    return {
        "type": "selection",
        "title": title,
        "message": message,
        "options": options,
        "context": context or {},
        "selection_type": "single",  # Only one can be selected
        "allow_none": True,  # User can choose "None of these"
        "none_label": "None of these files"
    }

async def execute_google_tool(db: Session, user_id: int, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute tools using google_services"""
    try:
        if tool_name == "check_calendar_availability": return await google_services.check_calendar_availability(db, user_id, arguments)
        elif tool_name == "schedule_calendar_event": return await google_services.schedule_calendar_event(db, user_id, arguments)
        elif tool_name == "update_calendar_event": return await google_services.update_calendar_event(db, user_id, arguments)
        elif tool_name == "delete_calendar_event": return await google_services.delete_calendar_event(db, user_id, arguments)
        elif tool_name == "send_email": return await google_services.send_email(db, user_id, arguments)
        elif tool_name == "read_emails": return await google_services.read_emails(db, user_id, arguments)
        elif tool_name == "delete_email": return await google_services.delete_email(db, user_id, arguments)
        elif tool_name == "update_email_labels": return await google_services.update_email_labels(db, user_id, arguments)
        elif tool_name == "list_drive_files": return await google_services.list_drive_files(db, user_id, arguments)
        elif tool_name == "upload_to_drive": return await google_services.upload_to_drive(db, user_id, arguments)
        elif tool_name == "update_drive_file": return await google_services.update_drive_file(db, user_id, arguments)
        elif tool_name == "delete_drive_file": return await google_services.delete_drive_file(db, user_id, arguments)
        elif tool_name == "read_drive_file_content": return await google_services.read_drive_file_content(db, user_id, arguments)
        elif tool_name == "create_spreadsheet": return await google_services.create_spreadsheet(db, user_id, arguments)
        elif tool_name == "read_spreadsheet": return await google_services.read_spreadsheet(db, user_id, arguments)
        elif tool_name == "update_spreadsheet_values": return await google_services.update_spreadsheet_values(db, user_id, arguments)
        elif tool_name == "clear_spreadsheet_values": return await google_services.clear_spreadsheet_values(db, user_id, arguments)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "error", "message": f"Tool '{tool_name}' not implemented"}

def get_hitl_form_schema(tool_id: str, missing_params: List[str]) -> Dict[str, Any]:
    """Generate form schema with tool metadata for missing parameters."""
    tool_def = next((t for t in TOOLS_REGISTRY if t["tool_id"] == tool_id), None)
    
    fields = []
    for param in missing_params:
        # Determine field type based on parameter name
        field_type = "text"
        if "email" in param.lower():
            field_type = "email"
        elif "date" in param.lower() or "time" in param.lower():
            field_type = "datetime"
        elif "body" in param.lower() or "content" in param.lower() or "description" in param.lower():
            field_type = "textarea"
        elif "days" in param.lower() or "size" in param.lower() or "results" in param.lower():
            field_type = "number"
        
        fields.append({
            "name": param,
            "label": param.replace("_", " ").title(),
            "type": field_type,
            "required": True,
            "placeholder": f"Enter {param.replace('_', ' ')}"
        })
    
    return {
        "title": f"Missing Information for {tool_id.replace('_', ' ').title()}",
        "description": tool_def.get("tool_description", "Please provide the following details to proceed.") if tool_def else "Please provide the following details to proceed.",
        "tool_info": {
            "id": tool_id,
            "usage": tool_def.get("exact_precise_tool_use", "") if tool_def else "",
            "required_params": tool_def.get("must_required_params", []) if tool_def else [],
            "optional_params": tool_def.get("optional_params", []) if tool_def else []
        },
        "fields": fields
    }

async def workflow_handler(websocket: WebSocket, client_openai):
    """Main WebSocket workflow handler with heartbeat, HITL, and LLM verification."""
    session_id = "unknown"
    db = None
    heartbeat_task = None
    last_pong_time = time.time()
    
    async def send_heartbeat():
        """Send periodic heartbeat pings to keep connection alive."""
        nonlocal last_pong_time
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not await safe_send(websocket, {"type": "ping", "timestamp": time.time()}):
                    print("[HEARTBEAT] Socket closed, stopping heartbeat pings")
                    break
                
                # Check if we've received a pong recently
                if time.time() - last_pong_time > HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT:
                    print(f"[HEARTBEAT] No pong received in {HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT}s, connection may be stale")
            except Exception as e:
                print(f"[HEARTBEAT] Error sending ping: {e}")
                break
    
    try:
        await websocket.accept()
        db = SessionLocal()
        user_id = 1  # Default for now
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                
                # Handle heartbeat pong
                if message_data.get("type") == "pong":
                    last_pong_time = time.time()
                    continue
                
                # Handle client heartbeat
                if message_data.get("type") == "heartbeat":
                    await websocket.send_text(json.dumps({"type": "heartbeat_ack", "timestamp": time.time()}))
                    continue
                
                user_message = message_data.get("message")
                session_id = message_data.get("session_id", "default")
                hitl_response = message_data.get("hitl_response")
            except Exception as e:
                print(f"[WS ERROR] Failed to parse message: {e}")
                continue

            try:
                if user_message:
                    print(f"[LOGGER] USER MESSAGE ({session_id}): {user_message}")

                state_m = WorkflowState(session_id, db, user_id)
                state = await state_m.load()
                
                # --- AUTO-RESET STATE FOR NEW MESSAGES ---
                # If we get a fresh user message (not a HITL response),
                # we should clear any old plan and pending HITL to allow a new one to be generated.
                # EXCEPTION: If we have a pending tool, we only clear if it's NOT a confirmation/selection
                # that was interrupted. This allows some resilience to disconnects.
                if user_message and not hitl_response:
                    has_pending = bool(state.get("pending_tool"))
                    has_plan = bool(state.get("plan"))
                    
                    if has_pending or has_plan:
                        # If the user is just saying "yes" or "no" as a text message, 
                        # we might want to let the existing pending tool handle it.
                        # For now, we clear if it's a completely NEW intent.
                        print(f"[LOGGER] New message received ({session_id}). State cleanup: pending={has_pending}, plan={has_plan}")
                        state["plan"] = None
                        state["pending_tool"] = None
                        state["current_step"] = 0
                        state["execution_context"] = {}
                
                # --- HANDLE HITL RESPONSE ---
                if hitl_response and state.get("pending_tool"):
                    print(f"[LOGGER] HITL RESPONSE ({session_id}): {hitl_response}")
                    pending = state["pending_tool"]
                    
                    if pending["hitl_type"] == "form":
                        pending["arguments"].update(hitl_response)
                    elif pending["hitl_type"] == "selection":
                        selected_item = hitl_response.get("selected_item")
                        if not selected_item:
                            await safe_send(websocket, {"type": "content", "chunk": "No selection made. Action cancelled."})
                            state["pending_tool"] = None
                            state["current_step"] += 1
                            await state_m.save_message("assistant", "Action cancelled.", workflow_state=state)
                            # REMOVED premature 'done' signal
                            continue
                        
                        # Update variables for future steps with the selected ID
                        selected_id = selected_item.get("id")
                        selected_name = selected_item.get("name")
                        
                        # Add to execution context
                        state["execution_context"]["selected_file_id"] = selected_id
                        state["execution_context"]["selected_file_name"] = selected_name
                        
                        # Specifically update file_id for next steps if they need it
                        for future_step in state.get("plan", [])[state["current_step"] + 1:]:
                            if "file_id" in future_step.get("variables", {}):
                                future_step["variables"]["file_id"] = selected_id
                            if "missing_variables" in future_step and "file_id" in future_step["missing_variables"]:
                                future_step["missing_variables"].remove("file_id")
                                future_step["variables"]["file_id"] = selected_id

                        await safe_send(websocket, {"type": "content", "chunk": f"Selected file: {selected_name}"})
                        state["pending_tool"] = None
                        state["current_step"] += 1
                        await state_m.save_message("assistant", f"User selected file: {selected_name}", workflow_state=state)
                        # Workflow continues in the next loop iteration
                    elif pending["hitl_type"] == "confirmation":
                        if hitl_response.get("approved") is False:
                            await safe_send(websocket, {"type": "content", "chunk": "Action cancelled."})
                            state["pending_tool"] = None
                            state["current_step"] += 1  # Advance to next step even if cancelled
                            await state_m.save_message("assistant", "Action cancelled.", workflow_state=state)
                            # REMOVED premature 'done' signal
                            continue
                    
                    if pending["hitl_type"] == "form":
                        # Save user's input to history so LLM can see it in the next resolution pass
                        input_summary = ", ".join([f"{k}: {v}" for k, v in hitl_response.items()])
                        await state_m.save_message("user", f"I've provided the missing details: {input_summary}", workflow_state=state)
                        
                        # Use the new resolution loop
                        pending["arguments"].update(hitl_response)
                        missing = [] # Will be checked by second pass resolution
                    
                    # Special check: If this was a selection, we've already updated the context and future steps.
                    # We should NOT re-execute the search tool (e.g. list_drive_files), 
                    # but we MUST let the code fall through to the 'while state.get("plan")' loop below
                    # so that it picks up the NEXT step in the plan.
                    if pending.get("hitl_type") == "selection":
                        print(f"[LOGGER] Selection handled for {pending['name']}, proceeding to next step.")
                        state["pending_tool"] = None
                        # Note: current_step was already incremented in the selection branch above
                    
                    elif not missing:
                        # Execute the tool
                        await safe_send(websocket, {"type": "status", "message": "executing_tool", "tool_name": pending["name"]})
                        result = await execute_google_tool(db, user_id, pending["name"], pending["arguments"])
                        print(f"[LOGGER] TOOL EXECUTION ({pending['name']}): {result}")
                        await safe_send(websocket, {"type": "tool_result", "tool_name": pending["name"], "result": result})
                        
                        # CHECK FOR TOOL ERROR - break stream immediately
                        if result.get("status") == "error" or result.get("error"):
                            error_msg = result.get("message") or result.get("error") or "Tool execution failed"
                            print(f"[TOOL ERROR] {pending['name']}: {error_msg}")
                            await safe_send(websocket, {
                                "type": "error", 
                                "message": f"Tool '{pending['name']}' failed: {error_msg}",
                                "tool_name": pending["name"],
                                "recoverable": True
                            })
                            # Clear pending and reset state
                            state["pending_tool"] = None
                            state["plan"] = None
                            state["execution_context"] = {}
                            await state_m.save_message("assistant", f"Error: {error_msg}", workflow_state=state)
                            await safe_send(websocket, {"type": "workflow_complete", "status": "error", "session_id": session_id})
                            continue
                        
                        # LLM Verification for successful execution
                        remaining_plan = state.get("plan", [])[state["current_step"] + 1:] if state.get("plan") else []
                        verification = await verify_step_result(
                            client_openai, 
                            pending["name"], 
                            pending["arguments"], 
                            result,
                            state.get("user_goal", ""),
                            remaining_plan,
                            state.get("execution_context", {})
                        )
                        print(f"[LOGGER] VERIFICATION ({pending['name']}): {verification}")
                        
                        # Update execution context with verified results
                        if verification.get("context_for_next_step"):
                            state["execution_context"].update(verification["context_for_next_step"])
                        if verification.get("updated_variables"):
                            for future_step in state.get("plan", [])[state["current_step"] + 1:]:
                                future_step["variables"].update(verification["updated_variables"])
                        
                        state["pending_tool"] = None
                        state["current_step"] += 1
                        await state_m.save_message("tool", content=json.dumps(result), tool_name=pending["name"], workflow_state=state)
                        
                        # Check if verification says to stop
                        if not verification.get("should_continue", True):
                            await safe_send(websocket, {"type": "content", "chunk": verification.get("error_recovery", "Workflow stopped due to error.")})
                            await safe_send(websocket, {"type": "workflow_complete", "status": "stopped", "session_id": session_id})
                            # Add 'done' here as it's a stopping point
                            await safe_send(websocket, {"type": "done", "session_id": session_id})
                            continue
                    else:
                        schema = get_hitl_form_schema(pending["name"], missing)
                        await safe_send(websocket, {"type": "hitl_form", "schema": schema})
                        await state_m.save_message("assistant", "Missing parameters for tool.", hitl_type="form", hitl_schema=schema, workflow_state=state)
                        continue

                # --- SAVE USER MESSAGE if present ---
                if user_message:
                    state["user_goal"] = user_message  # Store for verification context
                    await state_m.save_message("user", user_message, workflow_state=state)

                # --- INITIAL PLANNER CALL ---
                if user_message and not state.get("plan"):
                    try:
                        await safe_send(websocket, {"type": "status", "message": "thinking"})
                        extracted = await extract_variables(client_openai, user_message)
                        print(f"[LOGGER] EXTRACTED VARIABLES ({session_id}): {json.dumps(extracted, indent=2)}")
                    except Exception as extract_error:
                        print(f"[ERROR] Variable extraction failed: {extract_error}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Failed to analyze your request: {str(extract_error)}",
                            "stage": "variable_extraction",
                            "recoverable": True
                        }))
                        await websocket.send_text(json.dumps({"type": "workflow_complete", "status": "error", "session_id": session_id}))
                        continue
                    
                    try:
                        await safe_send(websocket, {"type": "status", "message": "choosing_tools"})
                        plan = await plan_workflow(client_openai, user_message, TOOLS_REGISTRY, extracted)
                        
                        print(f"[LOGGER] OPENAI PLANNER ({session_id}): {json.dumps(plan, indent=2)}")
                        
                        # Check if plan is empty or invalid
                        if not plan or len(plan) == 0:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "I couldn't determine which tools to use. Please try rephrasing your request.",
                                "stage": "planning",
                                "recoverable": True
                            }))
                            await websocket.send_text(json.dumps({"type": "workflow_complete", "status": "error", "session_id": session_id}))
                            continue
                        
                        # Send plan preview to user
                        await safe_send(websocket, {
                            "type": "plan_preview",
                            "plan": plan,
                            "extracted_variables": extracted
                        })
                        
                        state["plan"] = plan
                        state["current_step"] = 0
                        state["execution_context"] = extracted.copy()  # Initialize with extracted vars
                    except Exception as plan_error:
                        print(f"[ERROR] Planning failed: {plan_error}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": f"Failed to create execution plan: {str(plan_error)}",
                            "stage": "planning",
                            "extracted_variables": extracted if 'extracted' in dir() else {},
                            "recoverable": True
                        }))
                        await websocket.send_text(json.dumps({"type": "workflow_complete", "status": "error", "session_id": session_id}))
                        continue
                
                # --- EXECUTE PLAN ---
                while state.get("plan") and state["current_step"] < len(state["plan"]):
                    step = state["plan"][state["current_step"]]
                    tool_name = step.get("tool_id")
                    
                    # DYNAMIC PARAMETER RESOLUTION
                    # Fetch full history to inform the LLM
                    history = await state_m.get_full_history()
                    resolution = await resolve_step_parameters(
                        client_openai, 
                        tool_name, 
                        state.get("user_goal", ""), 
                        history, 
                        state.get("execution_context", {}), 
                        step, 
                        TOOLS_REGISTRY
                    )
                    
                    merged_args = resolution.get("arguments", {})
                    missing = resolution.get("missing_params", [])
                    
                    tool_def = next((t for t in TOOLS_REGISTRY if t["tool_id"] == tool_name), None)
                    if not tool_def: 
                        state["current_step"] += 1
                        continue
                    
                    # Check for missing required params
                    if missing:
                        state["pending_tool"] = {"name": tool_name, "arguments": merged_args, "hitl_type": "form"}
                        schema = get_hitl_form_schema(tool_name, missing)
                        await safe_send(websocket, {"type": "hitl_form", "schema": schema})
                        await state_m.save_message("assistant", f"Need parameters for {tool_name}", hitl_type="form", hitl_schema=schema, workflow_state=state)
                        break 
                    
                    # Update context with resolved arguments
                    state["execution_context"].update(merged_args)

                    # Check for HITL confirmation (sensitive actions)
                    if tool_name in ["send_email", "schedule_calendar_event", "delete_calendar_event", "delete_drive_file", "delete_email"]:
                        state["pending_tool"] = {"name": tool_name, "arguments": merged_args, "hitl_type": "confirmation"}
                        await safe_send(websocket, {
                            "type": "hitl_confirmation", 
                            "title": "Confirm Action", 
                            "message": f"Proceed with {tool_name.replace('_', ' ').title()}?", 
                            "details": merged_args
                        })
                        await state_m.save_message("assistant", f"Confirmation needed for {tool_name}", hitl_type="confirmation", workflow_state=state)
                        break

                    # Execute tool
                    # SEPARATION OF CONCERNS: Send status as distinct event
                    await safe_send(websocket, {"type": "status", "message": "executing_tool", "tool_name": tool_name})
                    result = await execute_google_tool(db, user_id, tool_name, merged_args)
                    print(f"[LOGGER] TOOL EXECUTION ({tool_name}): {result}")
                    
                    # SPECIAL CASE: list_drive_files handles doc discovery
                    if tool_name == "list_drive_files":
                        files = result.get("files", [])
                        search_query = merged_args.get("filename") or merged_args.get("query") or ""
                        
                        # We ALWAYS run similarity search if we found 1 or more files
                        # to ensure consistent HITL experience or confident auto-picking.
                        if len(files) >= 1 :
                            print(f"[LOGGER] Drive results count: {len(files)} for query '{search_query}'. Running similarity search...")
                            
                            similarity_results = await find_similar_files(client_openai, search_query, files, user_goal=state.get("user_goal", ""))
                            best_match_id = similarity_results.get("best_match_id")
                            matches = similarity_results.get("matches", [])
                            
                            if best_match_id:
                                # Auto-pick the best match
                                best_match = next((m for m in matches if m["id"] == best_match_id), None)
                                print(f"[LOGGER] LLM auto-picked best match: {best_match.get('name') if best_match else best_match_id}")
                                
                                # Update result to simulate a single successful find
                                if best_match:
                                    result["files"] = [best_match]
                                    selected_name = best_match.get("name", "selected file")
                                else:
                                    selected_name = "selected file"
                                
                                # SEPARATE MESSAGE for selection notification
                                await safe_send(websocket, {
                                    "role": "assistant", 
                                    "content": f"Found and selected: {selected_name}",
                                    "type": "content"
                                })
                                await safe_send(websocket, {"type": "tool_result", "tool_name": tool_name, "result": result})
                            elif matches:
                                # Decision needed
                                state["pending_tool"] = {"name": tool_name, "arguments": merged_args, "hitl_type": "selection"}
                                options = []
                                is_sheet = any("spreadsheet" in m.get("mimeType", "").lower() for m in matches)
                                
                                for m in matches:
                                    label = f"[{m.get('relevance_label', 'Match')}]"
                                    options.append({
                                        "id": m["id"], 
                                        "name": f"{label} {m['name']}", 
                                        "description": m["reason"]
                                    })
                                
                                title = "Spreadsheet Selection" if is_sheet else "File Selection"
                                msg = f"I found several { 'spreadsheets' if is_sheet else 'files' } matching '{search_query}'. Which one should I use?"
                                
                                schema = get_hitl_selection_schema(title=title, message=msg, options=options)
                                await safe_send(websocket, {"type": "hitl_selection", "schema": schema})
                                await state_m.save_message("assistant", f"Selection needed for {search_query}", hitl_type="selection", hitl_schema=schema, workflow_state=state)
                                break 
                            else:
                                # No good matches found by LLM filter
                                await safe_send(websocket, {"type": "tool_result", "tool_name": tool_name, "result": result})
                        else:
                            # 0 files found or error
                            await safe_send(websocket, {"type": "tool_result", "tool_name": tool_name, "result": result})
                    else:
                        await safe_send(websocket, {"type": "tool_result", "tool_name": tool_name, "result": result})
                    
                    # CHECK FOR TOOL ERROR - break stream immediately
                    if result.get("status") == "error" or result.get("error"):
                        error_msg = result.get("message") or result.get("error") or "Tool execution failed"
                        print(f"[TOOL ERROR] {tool_name}: {error_msg}")
                        await safe_send(websocket, {
                            "type": "error", 
                            "message": f"Tool '{tool_name}' failed: {error_msg}",
                            "tool_name": tool_name,
                            "recoverable": True
                        })
                        # Clear state and stop workflow
                        state["plan"] = None
                        state["execution_context"] = {}
                        await state_m.save_message("assistant", f"Error: {error_msg}", workflow_state=state)
                        await safe_send(websocket, {"type": "workflow_complete", "status": "error", "session_id": session_id})
                        break
                    
                    # LLM Verification for each step
                    remaining_plan = state["plan"][state["current_step"] + 1:]
                    verification = await verify_step_result(
                        client_openai, 
                        tool_name, 
                        merged_args, 
                        result,
                        state.get("user_goal", ""),
                        remaining_plan,
                        state.get("execution_context", {})
                    )
                    print(f"[LOGGER] VERIFICATION ({tool_name}): {verification}")
                    
                    # Update execution context
                    if verification.get("context_for_next_step"):
                        state["execution_context"].update(verification["context_for_next_step"])
                    if verification.get("updated_variables"):
                        for future_step in state["plan"][state["current_step"] + 1:]:
                            future_step["variables"].update(verification["updated_variables"])
                    
                    # SPECIAL CASE: If tool result indicates a PDF was read, trigger the UI viewer
                    if tool_name == "read_drive_file_content" and result.get("is_pdf"):
                        file_id = result.get("file_id")
                        # Send view_pdf event
                        await safe_send(websocket, {
                            "type": "view_pdf",
                            "file_id": file_id,
                            "file_name": result.get("name"),
                            "proxy_url": f"/api/drive/view/{file_id}"
                        })

                    state["current_step"] += 1
                    await state_m.save_message("tool", content=json.dumps(result), tool_name=tool_name, workflow_state=state)
                    
                    # Check if verification says to stop
                    if not verification.get("should_continue", True):
                        await safe_send(websocket, {"role": "assistant", "content": verification.get("error_recovery", "Workflow stopped."), "type": "content"})
                        await safe_send(websocket, {"type": "workflow_complete", "status": "stopped", "session_id": session_id})
                        await safe_send(websocket, {"type": "done", "session_id": session_id})
                        break

                # --- FINAL STRUCTURED RESPONSE ---
                if (user_message or hitl_response) and state.get("pending_tool") is None:
                    # Only generate final response if no pending HITL
                    plan_complete = not state.get("plan") or state["current_step"] >= len(state.get("plan", []))
                    
                    if plan_complete or not state.get("plan"):
                        try:
                            history = await state_m.get_full_history()
                            history.append({"role": "system", "content": "Generate the final response using the specified structured format."})
                            response = await client_openai.chat.completions.create(
                                model="gpt-4o",
                                messages=history[-15:],
                                response_format=FORMAT_SCHEMA
                            )
                            structured_data = json.loads(response.choices[0].message.content)
                            print(f"[LOGGER] OPENAI ASSISTANT ({session_id}): {json.dumps(structured_data, indent=2)}")
                            # REMOVED finished: True from content chunk
                            await safe_send(websocket, {"type": "content", "chunk": json.dumps(structured_data)})
                            
                            state["plan"] = None 
                            state["execution_context"] = {}
                            await state_m.save_message("assistant", json.dumps(structured_data), workflow_state=state)
                            
                            # Send clear completion signal
                            await safe_send(websocket, {
                                "type": "workflow_complete", 
                                "status": "success",
                                "session_id": session_id,
                                "message": "Workflow completed successfully"
                            })
                            await safe_send(websocket, {"type": "done", "session_id": session_id})
                        except json.JSONDecodeError as json_err:
                            print(f"[ERROR] Failed to parse LLM response: {json_err}")
                            await safe_send(websocket, {
                                "type": "error",
                                "message": "Failed to generate final response. Please try again.",
                                "stage": "response_generation",
                                "recoverable": True
                            })
                            await safe_send(websocket, {"type": "workflow_complete", "status": "error", "session_id": session_id})
                        except Exception as response_error:
                            print(f"[ERROR] Final response generation failed: {response_error}")
                            await safe_send(websocket, {
                                "type": "error",
                                "message": f"Error generating response: {str(response_error)}",
                                "stage": "response_generation",
                                "recoverable": True
                            })
                            await safe_send(websocket, {"type": "workflow_complete", "status": "error", "session_id": session_id})

            except Exception as e:
                error_details = str(e)
                print(f"[WS ERROR] Processing error (Session: {session_id}): {e}")
                traceback.print_exc()
                # Use safe_send to prevent cascading errors when connection is closed
                await safe_send(websocket, {
                    "type": "error", 
                    "message": f"Unexpected error: {error_details}",
                    "stage": "processing",
                    "session_id": session_id,
                    "recoverable": True
                })
                await safe_send(websocket, {"type": "workflow_complete", "status": "error", "session_id": session_id})

    except (WebSocketDisconnect, RuntimeError) as e:
        print(f"WS Disconnected (Session: {session_id}): {type(e).__name__}")
    except Exception as e:
        print(f"WS Error (Session: {session_id}): {e}")
        traceback.print_exc()
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        if db: db.close()

async def stream_openai_response_async(client_openai, messages, tools=None):
    kwargs = {"model": "gpt-4o", "messages": messages, "stream": True}
    if tools: kwargs.update({"tools": tools, "tool_choice": "auto"})
    
    stream = await client_openai.chat.completions.create(**kwargs)
    full_c, tool_calls = "", []
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta:
            delta = chunk.choices[0].delta
            if delta.content:
                full_c += delta.content
                yield {"type": "content", "chunk": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    while len(tool_calls) <= tc.index:
                        tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    call = tool_calls[tc.index]
                    if tc.id: call["id"] += tc.id
                    if tc.function.name: call["function"]["name"] += tc.function.name
                    if tc.function.arguments: call["function"]["arguments"] += tc.function.arguments
    yield {"type": "complete", "content": full_c, "tool_calls": tool_calls if tool_calls else None}
