from package import *
from controller.workflow_execution_controller import workflow_handler


@router.websocket("/ws/workflow")
async def workflow_websocket_endpoint(websocket: WebSocket):
    # Retrieve dependencies from app.state
    client_openai = websocket.app.state.client_openai
    
    # Custom tools can be passed here if needed
    # For now, using default tools defined in the controller
    await workflow_handler(websocket, client_openai)
