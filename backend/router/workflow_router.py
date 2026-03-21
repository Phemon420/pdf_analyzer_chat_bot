from package import *
from controller.workflow_execution_controller import workflow_handler

from fastapi import Query
from function import function_token_decode

@router.websocket("/ws/workflow")
async def workflow_websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # Retrieve dependencies from app.state
    client_openai = websocket.app.state.client_openai
    config_key_jwt = getattr(websocket.app.state, "config_key_jwt", None)
    
    user = None
    if token and config_key_jwt:
        try:
            user = await function_token_decode(token, config_key_jwt)
        except:
            pass
            
    websocket.state.user = user
    
    # Custom tools can be passed here if needed
    # For now, using default tools defined in the controller
    await workflow_handler(websocket, client_openai)
