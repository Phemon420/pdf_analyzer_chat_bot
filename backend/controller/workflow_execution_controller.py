from package import *
import json
import time
import asyncio
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from agents import google_services
from fastapi import WebSocketDisconnect
from controller.thread_store import (
    get_or_create_thread, add_message,
    get_openai_history, get_messages
)

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

def get_openai_tools_from_registry() -> List[Dict[str, Any]]:
    # Replaced by internal sequential logic
    pass

local_workflow_cache = {}

class WorkflowState:
    def __init__(self, thread_id: str):
        self.thread_id = thread_id

    async def load(self) -> Dict[str, Any]:
        if self.thread_id in local_workflow_cache:
            return local_workflow_cache[self.thread_id]
        return {
            "workflow_id": None,
            "status": "active",
            "history": [],
            "previous_response_id": None,
            "pending_tool": None,
            "current_step": 0,
            "user_goal": None,
            "execution_context": {},
            "plan": None
        }

    async def save(self, state: Dict[str, Any]):
        if len(state.get("history", [])) > 20:
            state["history"] = state["history"][-20:]
        local_workflow_cache[self.thread_id] = state

    async def save_message(self, role: str, content: str = None, tool_name: str = None, hitl_type: str = None, hitl_schema: Dict = None, workflow_state: Dict = None):
        extra = {}
        if hitl_type:
            extra["hitl_type"] = hitl_type
        if hitl_schema:
            extra["hitl_schema"] = hitl_schema
        add_message(self.thread_id, role, content, tool_name=tool_name, extra=extra if extra else None)
        if workflow_state:
            await self.save(workflow_state)

    async def get_full_history(self) -> List[Dict]:
        return get_openai_history(self.thread_id)

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

def get_current_ist_time() -> str:
    """Returns the current date and time in IST format."""
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    return now_ist.strftime("%A, %Y-%m-%d %H:%M:%S IST")

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
    print(f"[LOGGER] AI RESPONSE (extract_variables): {response.choices[0].message.content}")
    extracted = json.loads(response.choices[0].message.content)
    # Remove null values
    return {k: v for k, v in extracted.items() if v is not None and v != ""}

async def plan_workflow(client_openai, user_message: str, history: List[Dict], current_time: str) -> Dict[str, Any]:
    """Uses LLM to create a step-by-step plan for the user's request with IST time context."""
    tools_context = json.dumps(TOOLS_REGISTRY, indent=2)
    system_prompt = f"""
    You are an expert Workflow Planner for a Google Services agent (Gmail, Drive, Calendar).
    Current Time (IST): {current_time}
    Available Tools: {tools_context}
    
    CRITICAL RULES:
    1. Resolve all relative dates (today, tomorrow, next week) using the provided IST time.
    2. Respond ONLY with a JSON object.
    3. Use provided tool definitions from the context.
    4. If a step depends on another, use "output_from_step_X" as the variable value.
    5. Identify missing parameters if they are not in the message or history.
    
    JSON Schema:
    {{
        "plan": [
            {{
                "step": 1,
                "tool_id": "tool_name",
                "variables": {{ "arg1": "val1" }},
                "missing_variables": ["name"],
                "description": "Short explanation",
                "depends_on_step": null,
                "output_used_by": [2]
            }}
        ],
        "summary": "High level plan description"
    }}
    """
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User Goal: {user_message}\nHistory: {json.dumps(history)}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[PLANNING ERROR] {e}")
        return {"plan": [], "summary": "Failed to generate plan."}

async def verify_step_result(client_openai, tool_name: str, tool_args: Dict, tool_result: Dict, user_goal: str, remaining_plan: List[Dict], execution_context: Dict) -> Dict[str, Any]:
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
        print(f"[LOGGER] AI RESPONSE (verify_step_result): {response.choices[0].message.content}")
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
        print(f"[LOGGER] AI RESPONSE (find_similar_files): {response.choices[0].message.content}")
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[SIMILARITY SEARCH ERROR] {e}")
        return {"matches": [], "message": f"Search failed: {str(e)}"}

async def resolve_step_parameters(client_openai, tool_name: str, user_goal: str, history: List[Dict], context: Dict, step_def: Dict, tools_registry: List[Dict]) -> Dict[str, Any]:
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
        print(f"[LOGGER] AI RESPONSE (resolve_step_parameters): {response.choices[0].message.content}")
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

async def extract_params_from_hitl(client_openai, tool_id: str, user_input: str) -> Dict[str, Any]:
    """Step 4: LLM call to extract parameters from user input based on tool definition."""
    tool_def = next((t for t in TOOLS_REGISTRY if t["tool_id"] == tool_id), None)
    if not tool_def:
        return {}

    prompt = f"""
    The user is providing information for the tool: "{tool_id}"
    Tool Description: {tool_def.get('tool_description')}
    Required Parameters: {tool_def.get('must_required_params')}
    Optional Parameters: {tool_def.get('optional_params')}
    
    User's Input: "{user_input}"
    
    Extract the relevant parameters from the input. Return ONLY a JSON object.
    """
    try:
        response = await client_openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data extraction engine. Extract parameters accurately into JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[EXTRACTION ERROR] {e}")
        return {}

async def execute_google_tool(tool_name: str, arguments: Dict[str, Any], user_id: int) -> Dict[str, Any]:
    """Execute tools directly using the local agents package (bypassing MCP)."""
    db = SessionLocal()
    try:
        # Step 2: Tool execution handled by local files
        if not hasattr(google_services, tool_name):
            return {"status": "error", "message": f"Tool '{tool_name}' not found locally."}
        
        func = getattr(google_services, tool_name)
        print(f"[LOGGER] EXECUTING LOCAL TOOL: {tool_name} for user {user_id}")
        
        # All modular tools in agents/ follow the signature: (db, user_id, parameters)
        result = await func(db, user_id, arguments)
        return result
    except Exception as e:
        print(f"[LOCAL EXECUTION ERROR] {tool_name}: {str(e)}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

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

async def resolve_parameters(client_openai, tool_id: str, variables: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves output_from_step_X placeholders and refines email content."""
    resolved = variables.copy()
    context = state.get("execution_context", {})
    
    # 1. Resolve placeholders like output_from_step_1
    for key, value in resolved.items():
        if isinstance(value, str) and "output_from_step_" in value:
            try:
                # Find step number
                import re
                match = re.search(r"output_from_step_(\d+)", value)
                if match:
                    step_num = match.group(1)
                    step_key = f"step_{step_num}_result"
                    if step_key in context:
                        result = context[step_key]
                        # Mapping logic for different tool outputs
                        if isinstance(result, dict):
                            if "id" in result: resolved[key] = result["id"]
                            elif "content" in result: resolved[key] = result["content"]
                            elif "files" in result and len(result["files"]) > 0:
                                resolved[key] = result["files"][0]["id"]
                            else: resolved[key] = str(result)
                        else:
                            resolved[key] = str(result)
            except Exception as e:
                print(f"[RESOLVE ERROR] Failed to resolve {value}: {e}")

    # 2. Email Refinement ("Write down more betterly")
    if tool_id == "send_email" and resolved.get("body"):
        print(f"[LOGGER] Refining email body for more professional tone...")
        prompt = f"""
        Refine the following email body to be professional, well-structured, and clear. 
        Maintain all key information but improve the tone and formatting.
        Raw Content: {resolved['body']}
        
        Return ONLY the improved email body.
        """
        try:
            response = await client_openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional communication expert."},
                    {"role": "user", "content": prompt}
                ]
            )
            resolved["body"] = response.choices[0].message.content
        except Exception as e:
            print(f"[REFINEMENT ERROR] {e}")
            
    return resolved

async def workflow_handler(websocket: WebSocket, client_openai):
    session_id = "unknown"
    heartbeat_task = None
    last_pong_time = time.time()

    async def send_heartbeat():
        nonlocal last_pong_time
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not await safe_send(websocket, {"type": "ping", "timestamp": time.time()}):
                    break
                if time.time() - last_pong_time > HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT:
                    print(f"[HEARTBEAT] No pong in {HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT}s")
            except Exception as e:
                print(f"[HEARTBEAT] Error: {e}")
                break

    try:
        await websocket.accept()
        user = getattr(websocket.state, "user", None)
        user_id = user["id"] if user and "id" in user else 1

        heartbeat_task = asyncio.create_task(send_heartbeat())
        
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                if message_data.get("type") == "pong":
                    last_pong_time = time.time()
                    continue
                if message_data.get("type") == "heartbeat":
                    await websocket.send_text(json.dumps({"type": "heartbeat_ack", "timestamp": time.time()}))
                    continue

                user_message = message_data.get("message")
                incoming_thread_id = message_data.get("session_id")
                hitl_response = message_data.get("hitl_response")
            except Exception as e:
                print(f"[WS ERROR] Failed to parse message: {e}")
                continue

            try:
                thread = get_or_create_thread(incoming_thread_id)
                session_id = thread["id"]

                state_m = WorkflowState(session_id)
                state = await state_m.load()
                
                # Get Current IST Time for LLM Context
                current_time_ist = get_current_ist_time()
                print(f"[LOGGER] Processing message with IST Time Context: {current_time_ist}")

                # --- STEP 1: PLANNING (FIRST CALL) ---
                if user_message and not hitl_response:
                    print(f"[LOGGER] USER MESSAGE ({session_id}): {user_message}")
                    await state_m.save_message("user", user_message, workflow_state=state)
                    state["user_goal"] = user_message
                    
                    state["plan"] = None
                    state["pending_tool"] = None
                    state["current_step"] = 0
                    state["execution_context"] = {}
                    
                    await safe_send(websocket, {"type": "status", "message": "planning"})
                    # Planning uses tool registry as reference (Step 1)
                    history = await state_m.get_full_history()
                    plan_data = await plan_workflow(client_openai, user_message, history, current_time_ist)
                    print(f"[LOGGER] PLAN GENERATED: {json.dumps(plan_data, indent=2)}")
                    
                    state["plan"] = plan_data.get("plan", [])
                    await state_m.save(state)
                    await safe_send(websocket, {"type": "plan_preview", "plan": state["plan"]})

                # --- STEP 4: PARAMETER EXTRACTION FROM HITL ---
                if hitl_response and state.get("pending_tool"):
                    pending = state["pending_tool"]
                    tool_id = pending["name"]
                    user_input_text = json.dumps(hitl_response)
                    
                    await safe_send(websocket, {"type": "status", "message": "extracting_params"})
                    # Extract params using LLM (Step 4)
                    extracted = await extract_params_from_hitl(client_openai, tool_id, user_input_text)
                    print(f"[LOGGER] EXTRACTED FROM HITL: {json.dumps(extracted, indent=2)}")
                    
                    # Merge into context and clear pending state
                    state["execution_context"].update(extracted)
                    state["pending_tool"] = None
                    await state_m.save_message("user", f"Provided info: {user_input_text}", workflow_state=state)

                # --- STEPS 2-5: SEQUENTIAL EXECUTION LOOP ---
                while state.get("plan") and state["current_step"] < len(state["plan"]):
                    step = state["plan"][state["current_step"]]
                    tool_id = step.get("tool_id")
                    
                    # Resolve variables (Planning vars + collected context)
                    current_args = step.get("variables", {}).copy()
                    current_args.update(state["execution_context"])
                    
                    # Step 3: Check for missing required params
                    tool_def = next((t for t in TOOLS_REGISTRY if t["tool_id"] == tool_id), None)
                    required = tool_def.get("must_required_params", []) if tool_def else []
                    missing = [p for p in required if p not in current_args or current_args[p] in (None, "", "null")]
                    
                    if missing:
                        print(f"[LOGGER] TOOL {tool_id} MISSING PARAMS: {missing}")
                        state["pending_tool"] = {"name": tool_id, "arguments": current_args, "hitl_type": "form"}
                        schema = get_hitl_form_schema(tool_id, missing)
                        await safe_send(websocket, {"type": "hitl_form", "schema": schema})
                        await state_m.save_message("assistant", f"I need more information to {tool_id.replace('_', ' ')}.", hitl_type="form", hitl_schema=schema, workflow_state=state)
                        break # Pause loop for user input
                    
                    # Step 2: Parameter Resolution (Fixing placeholders & Email improvement)
                    await safe_send(websocket, {"type": "status", "message": "resolving_params"})
                    resolved_args = await resolve_parameters(client_openai, tool_id, current_args, state)
                    
                    # Step 2: Tool execution (Bypassing MCP, calling local)
                    await safe_send(websocket, {
                        "type": "status", 
                        "message": "executing_tool", 
                        "tool_name": tool_id,
                        "arguments": resolved_args
                    })
                    
                    # Broadcast the tool call details to the UI
                    await safe_send(websocket, {
                        "type": "tool_call",
                        "tool_name": tool_id,
                        "arguments": resolved_args,
                        "step": state["current_step"] + 1
                    })

                    result = await execute_google_tool(tool_id, resolved_args, user_id)
                    print(f"[LOGGER] TOOL RESULT ({tool_id}): {result}")
                    
                    # Broadcast the tool result to the UI
                    await safe_send(websocket, {
                        "type": "tool_result", 
                        "tool_name": tool_id, 
                        "result": result,
                        "step": state["current_step"] + 1
                    })
                    
                    # Update context for next steps
                    await state_m.save_message("tool", content=json.dumps(result), tool_name=tool_id, workflow_state=state)
                    
                    # Store step result explicitly for placeholder resolution
                    step_key = f"step_{state['current_step'] + 1}_result"
                    state["execution_context"][step_key] = result
                    
                    if isinstance(result, dict) and result.get("status") == "success":
                         state["execution_context"].update(result)
                    
                    state["current_step"] += 1
                    await state_m.save(state)

                # --- STEP 5: FINAL NATURAL RESPONSE ---
                plan_complete = state.get("plan") and state["current_step"] >= len(state["plan"])
                if plan_complete and state.get("pending_tool") is None:
                    await safe_send(websocket, {"type": "status", "message": "finalizing"})
                    history = await state_m.get_full_history()
                    
                    # Synthesize a natural answer (Step 5)
                    response = await client_openai.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant. Provide a natural, concise, and direct response based on the tool execution results. Avoid generic summaries or vague JSON. Just answer the user's initial request clearly."},
                            *history[-10:]
                        ]
                    )
                    final_text = response.choices[0].message.content
                    await safe_send(websocket, {"type": "content", "chunk": final_text})
                    await state_m.save_message("assistant", final_text, workflow_state=state)
                    
                    # Reset state for next interaction
                    state["plan"] = None
                    state["current_step"] = 0
                    state["execution_context"] = {}
                    await state_m.save(state)
                    await safe_send(websocket, {"type": "done", "session_id": session_id})

            except Exception as e:
                print(f"[WS ERROR] Processing error: {e}")
                traceback.print_exc()
                await safe_send(websocket, {"type": "error", "message": str(e), "recoverable": True})

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
