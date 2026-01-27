from package import *
import json
import traceback
from typing import Optional, Dict, Any, List

# Memory fallback for chat history
local_chat_history = {}

async def websocket_handler(websocket: WebSocket, client_openai, redis_client):
    try:
        await websocket.accept()
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                user_message = message_data.get("message")
                session_id = message_data.get("session_id", "default_session")
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
                continue

            if not user_message:
                continue

            # State Management: Retrieve history from Redis or Local Fallback
            history_key = f"chat_history:{session_id}"
            history = []
            try:
                if redis_client:
                    raw_history = await redis_client.get(history_key)
                    if raw_history:
                        history = json.loads(raw_history)
                else:
                    history = local_chat_history.get(session_id, [])
            except Exception as e:
                print(f"[REDIS FALLBACK] Error loading chat history: {e}")
                history = local_chat_history.get(session_id, [])

            # Append user message
            history.append({"role": "user", "content": user_message})

            # Define tools (Example as requested)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "check_calendar_availability",
                        "description": "Check calendar availability for the next 7 days.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "days": {
                                    "type": "integer",
                                    "description": "Number of days to check ahead (default: 7)"
                                }
                            }
                        }
                    }
                }
            ]

            # Call OpenAI
            try:
                # First response stream
                stream = client_openai.chat.completions.create(
                    model="gpt-4o",
                    messages=history,
                    tools=tools,
                    tool_choice="auto",
                    stream=True
                )

                full_response_content = ""
                tool_calls = []
                
                # Iterate through the stream
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content_chunk = delta.content
                        full_response_content += content_chunk
                        # Send text chunk to client
                        await websocket.send_text(json.dumps({
                            "type": "content",
                            "chunk": content_chunk
                        }))
                    
                    if delta.tool_calls:
                        for tc in delta.tool_calls:
                            if len(tool_calls) <= tc.index:
                                tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                            
                            call = tool_calls[tc.index]
                            if tc.id: call["id"] += tc.id
                            if tc.function.name: call["function"]["name"] += tc.function.name
                            if tc.function.arguments: call["function"]["arguments"] += tc.function.arguments

                # Handle Tool Calls if any
                if tool_calls:
                    # Append assistant's tool call message to history
                    assistant_msg = {
                        "role": "assistant",
                        "content": full_response_content if full_response_content else None,
                        "tool_calls": tool_calls
                    }
                    history.append(assistant_msg)
                    
                    # Notify client about tool call (optional, for debugging/UI)
                    await websocket.send_text(json.dumps({
                        "type": "tool_call",
                        "calls": tool_calls
                    }))

                    # Execute workflow/tools (Mock execution for now as requested)
                    for tool_call in tool_calls:
                        function_name = tool_call["function"]["name"]
                        arguments = tool_call["function"]["arguments"]
                        
                        # Mock result
                        result_content = json.dumps({"status": "aborted", "reason": "Workflow execution pending implementation"})
                        
                        if function_name == "check_calendar_availability":
                             result_content = json.dumps({"available_slots": ["09:00", "14:00"], "status": "success"})

                        # Append tool result to history
                        history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_content
                        })

                    # Second call to OpenAI with tool results
                    stream_2 = client_openai.chat.completions.create(
                        model="gpt-4o",
                        messages=history,
                        stream=True
                    )
                    
                    full_final_content = ""
                    for chunk in stream_2:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            content_chunk = delta.content
                            full_final_content += content_chunk
                            await websocket.send_text(json.dumps({
                                "type": "content",
                                "chunk": content_chunk
                            }))
                    
                    history.append({"role": "assistant", "content": full_final_content})

                else:
                    # No tool calls, just append the content
                    history.append({"role": "assistant", "content": full_response_content})

            except Exception as e:
                print(f"OpenAI Error: {e}")
                traceback.print_exc()
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
                continue

            if len(history) > 20:
                history = history[-20:]
            
            try:
                if redis_client:
                    await redis_client.set(history_key, json.dumps(history))
                else:
                    local_chat_history[session_id] = history
            except Exception as e:
                print(f"[REDIS FALLBACK] Error saving chat history: {e}")
                local_chat_history[session_id] = history

            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        traceback.print_exc()
