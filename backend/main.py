from package import *
from function import *

# Load environment variables from .env file
load_dotenv()

config_cors_origin_list=["*"]
config_postgres_url=os.environ.get("DATABASE_URL")
config_token_user_key_list = "id,username".split(",")
config_key_root = os.environ.get("config_key_root")
# config_gemini_key = os.environ.get("config_gemini_key")
config_openai_key = os.environ.get("OPENAI_API_KEY")
config_key_jwt = os.environ.get("config_key_jwt")
config_token_expire_sec = int(os.environ.get("config_token_expire_sec",259200))

from contextlib import asynccontextmanager, AsyncExitStack
import traceback
import sys
from pathlib import Path
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

@asynccontextmanager
async def lifespan(app:FastAPI):
    async with AsyncExitStack() as exit_stack:
        try:
            client_postgres=await function_client_read_postgres(config_postgres_url) if config_postgres_url else None
            # client_gemini = function_client_read_gemini(config_gemini_key) if config_gemini_key else None
            client_openai = function_client_read_openai(config_openai_key) if config_openai_key else None
            
            # Start MCP Client Subprocess
            server_params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).parent / "mcp_server.py")], env=os.environ.copy())
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            mcp_session = await exit_stack.enter_async_context(ClientSession(read, write))
            await mcp_session.initialize()
            app.state.mcp_client = mcp_session
            print("FastMCP standalone server started globally via Stdio.")
            
            app.state.client_postgres = client_postgres
            # app.state.client_gemini = client_gemini
            app.state.client_openai = client_openai
            app.state.config_key_root = config_key_root
            app.state.config_key_jwt = config_key_jwt
            app.state.config_token_expire_sec = config_token_expire_sec
            
            print("Database connection established successfully!")
            function_add_app_state({**globals(),**locals()}, app, ("config_","client_","cache_"))
            yield
        except Exception as e:
            print(f"Failed to establish database or MCP connection: {str(e)}")
            print(traceback.format_exc())
        finally:
            if hasattr(app.state, 'client_postgres') and app.state.client_postgres:
                await app.state.client_postgres.close()
                print("Database connection closed.")


#app
app=function_fastapi_app_read(True,lifespan)
function_add_cors(app,config_cors_origin_list)


# Include router
from pathlib import Path
router_dir_path = Path(__file__).parent / "router"
function_add_router(app, router_dir_path)


import uvicorn
async def function_server_start(app):
    # Embedding FastAPI in a larger async application Running multiple Uvicorn servers in the same process.Full control over startup/shutdown hooks.
    config=uvicorn.Config(app,host="0.0.0.0",port=8000)
    server=uvicorn.Server(config)
    await server.serve()


from fastapi import responses
def function_return_error(message):
   return responses.JSONResponse(status_code=400,content={"status":0,"message":message})

PUBLIC_PATHS = {
    "/auth/signup",
    "/auth/login",
    "/api/drive/view"
}

#middleware
from fastapi import Request,responses
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request: Request, api_function):
    try:
        start = time.time()
        api = request.url.path
        request.state.user = {}

        # 1. Skip Auth for Public Paths
        if api in PUBLIC_PATHS:
            print(f"[AUTH] Skipping token check for public path: {api}")
        else:
            # 2. Token Check with its own Try-Except
            try:
                request.state.user = await function_token_check(
                    request,
                    request.app.state.config_key_root,
                    request.app.state.config_key_jwt
                )
            except Exception as e:
                print(f"[AUTH ERROR] Token validation failed: {e}")
                # We don't crash here unless the route is strictly private
                if api.startswith(("/private", "/admin", "/my")):
                    return function_return_error(f"Authentication failed: {str(e)}")

        # 3. Handler Execution
        print(f"[ROUTE LOGGER] 🟢 HTTP Request STARTED: {request.method} {api}")
        try:
            response = await api_function(request)
            process_time = time.time() - start
            print(f"[ROUTE LOGGER] 🔴 HTTP Request COMPLETED: {request.method} {api} (Took {process_time:.4f}s)")
            return response
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[HANDLER ERROR] Error in {api}:\n{error_trace}")
            return function_return_error(str(e))

    except Exception as e:
        print(f"[CRITICAL MIDDLEWARE ERROR] {str(e)}")
        print(traceback.format_exc())
        return function_return_error("Internal server error in middleware")


if __name__ == "__main__":
    asyncio.run(function_server_start(app))