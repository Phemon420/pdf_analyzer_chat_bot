from package import *
from function import *

# Load environment variables from .env file
load_dotenv()

config_cors_origin_list=["*"]
config_postgres_url=os.environ.get("DATABASE_URL")
config_token_user_key_list = "id,username".split(",")
config_key_root = os.environ.get("config_key_root")
config_gemini_key = os.environ.get("config_gemini_key")
config_key_jwt = os.environ.get("config_key_jwt")
config_token_expire_sec = int(os.environ.get("config_token_expire_sec",259200))

from contextlib import asynccontextmanager
import traceback
@asynccontextmanager
async def lifespan(app:FastAPI):
    try:
        client_postgres=await function_client_read_postgres(config_postgres_url) if config_postgres_url else None
        client_gemini = function_client_read_gemini(config_gemini_key) if config_gemini_key else None
        app.state.client_postgres = client_postgres
        app.state.client_gemini = client_gemini
        app.state.config_key_root = config_key_root
        app.state.config_key_jwt = config_key_jwt
        app.state.config_token_expire_sec = config_token_expire_sec
        print("Database connection established successfully!")
        function_add_app_state({**globals(),**locals()}, app, ("config_","client_","cache_"))
        yield
    except Exception as e:
        print(f"Failed to establish database connection: {str(e)}")
        print(traceback.format_exc())
    finally:
        if hasattr(app.state, 'client_postgres_asyncpg') and app.state.client_postgres:
            await app.state.client_postgres.close()
            print("Database connection closed.")


app = FastAPI()

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
    "/auth/login"
}

#middleware
from fastapi import Request,responses
import time,traceback,asyncio
@app.middleware("http")
async def middleware(request,api_function):
    try:
        #start
        start=time.time()
        response_type=None
        response=None
        error=None
        api=request.url.path
        request.state.user={}
        #auth check
        request.state.user = await function_token_check(
            request,
            request.app.state.config_key_root,
            request.app.state.config_key_jwt
        )
        if not response:
            response=await api_function(request)
    #error
    except Exception as e:
        error=str(e)
        print("error is coming from middleware")
        response=function_return_error(error)
        response_type=5
        print(error)
    #final
    return response


if __name__ == "__main__":
    asyncio.run(function_server_start(app))