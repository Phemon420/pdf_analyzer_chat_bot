from package import *
from controller.websocket_controller import websocket_handler

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    # Retrieve dependencies from app.state
    # Note: In FastAPI WebSockets, app state is accessible via websocket.app.state
    client_openai = websocket.app.state.client_openai
    redis_client = getattr(websocket.app.state, "redis_client", None)
    
    await websocket_handler(websocket, client_openai, redis_client)
