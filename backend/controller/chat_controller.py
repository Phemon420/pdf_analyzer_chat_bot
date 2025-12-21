
# ==== MODULAR STREAMING FUNCTIONS ====

# async def function_create_streaming_generator(gemini_client, messages, session_id=None, is_continuation=False):
#     """Generic streaming generator for AI responses"""
#     try:
#         response = gemini_client.chat.completions.create(
#             model="gemini-2.0-flash",
#             messages=messages,
#             stream=True
#         )

#         full_text = ""
        
#         for chunk in response:
#             chunk_data = {}
            
#             # Extract content from chunk
#             if (hasattr(chunk, 'choices') and 
#                 chunk.choices and 
#                 hasattr(chunk.choices[0], 'delta') and 
#                 hasattr(chunk.choices[0].delta, 'content') and 
#                 chunk.choices[0].delta.content):
                
#                 content = chunk.choices[0].delta.content
#                 full_text += content
#                 chunk_data['chunk'] = content
#                 chunk_data['full_text'] = full_text
                
#                 if session_id:
#                     chunk_data['session_id'] = session_id
#                 if is_continuation:
#                     chunk_data['is_continuation'] = True

#                 print(content)
            
#             if chunk_data:
#                 yield f"data: {json.dumps(chunk_data)}\n\n"

#         # Yield final result for session management
#         yield (full_text, messages)

#     except Exception as e:
#         yield f"data: {json.dumps({'error': str(e), 'is_continuation': is_continuation})}\n\n"
#         yield ("", [])

# async def function_manage_email_session_start(messages, full_text, **kwargs):
#     """Create and store new email conversation session"""
#     session_id = str(uuid.uuid4())
    
#     email_chat_sessions[session_id] = {
#         'messages': messages + [{"role": "assistant", "content": full_text}],
#         'created_at': time.time()
#     }
    
#     return session_id

# async def function_manage_email_session_continue(messages, full_text, **kwargs):
#     """Update existing email conversation session"""
#     session_id = kwargs.get('session_id')
#     session_data = email_chat_sessions.get(session_id)
    
#     if session_data is None:
#         raise ValueError("Invalid session_id")
    
#     final_messages = messages + [{"role": "assistant", "content": full_text}]
#     email_chat_sessions[session_id] = {
#         'messages': final_messages,
#         'created_at': session_data['created_at'],
#         'updated_at': time.time()
#     }
    
#     return session_id

# async def function_get_email_session(session_id):
#     """Retrieve email conversation session"""
#     return email_chat_sessions.get(session_id)

# async def function_build_email_messages(system_prompt, user_prompt):
#     """Build initial messages for email conversation"""
#     return [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_prompt}
#     ]

# async def function_create_generic_stream_response(gemini_client, messages, session_management_func=None, **kwargs):
#     """Generic function to create streaming response with optional session management"""
    
#     async def generate():
#         try:
#             # Generate session ID if needed
#             session_id = kwargs.get('session_id', str(uuid.uuid4()) if session_management_func else None)
            
#             # Use modular streaming generator
#             generator = function_create_streaming_generator(
#                 gemini_client, 
#                 messages, 
#                 session_id=session_id, 
#                 is_continuation=kwargs.get('is_continuation', False)
#             )
            
#             full_text = ""
#             final_messages = []
            
#             # Stream the response
#             async for item in generator:
#                 if isinstance(item, tuple):  # Final result (full_text, messages)
#                     full_text, final_messages = item
#                     break
#                 else:  # Streaming data
#                     yield item
            
#             # Handle session management if provided
#             completion_data = {'completed': True, 'full_text': full_text}
            
#             if session_management_func:
#                 session_result = await session_management_func(final_messages, full_text, **kwargs)
#                 if isinstance(session_result, str):  # session_id returned
#                     completion_data['session_id'] = session_result
#                 elif isinstance(session_result, dict):  # additional data returned
#                     completion_data.update(session_result)
            
#             # Add any additional completion data
#             completion_data.update(kwargs.get('completion_data', {}))
            
#             # Send final completion message
#             yield f"data: {json.dumps(completion_data)}\n\n"

#         except Exception as e:
#             error_data = {'error': str(e)}
#             if kwargs.get('is_continuation'):
#                 error_data['is_continuation'] = True
#             yield f"data: {json.dumps(error_data)}\n\n"

#     return StreamingResponse(generate(), media_type="text/event-stream")

