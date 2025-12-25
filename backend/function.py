from fastapi import FastAPI
def function_fastapi_app_read(is_debug,lifespan):
    app=FastAPI(debug=is_debug,lifespan=lifespan)
    return app

from fastapi.middleware.cors import CORSMiddleware
def function_add_cors(app,config_cors_origin_list):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config_cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    return None

def function_add_app_state(var_dict,app,prefix_tuple):
    for k, v in var_dict.items():
        if k.startswith(prefix_tuple):
            setattr(app.state, k, v)

import sys
import importlib.util
from pathlib import Path
import traceback
def function_add_router(app, router_folder_path):
    router_root = Path(router_folder_path).resolve()
    if not router_root.is_dir():
        raise ValueError(f"router folder not found: {router_root}")
    def load_module(file_path):
        try:
            rel = file_path.relative_to(router_root)
            module_name = "routers." + ".".join(rel.with_suffix("").parts)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            if hasattr(module, "router"):
                app.include_router(module.router)
        except Exception:
            print(f"[WARN] failed to load router: {file_path}")
            traceback.print_exc()
    for file_path in router_root.rglob("*.py"):
        if not file_path.name.startswith("__"):
            load_module(file_path)
    return None


import jwt,json,time
async def function_token_encode(config_key_jwt,config_token_expire_sec,object,user_key_list):
    data=dict(object)
    payload={k:data.get(k) for k in user_key_list}
    payload=json.dumps(payload,default=str)
    token=jwt.encode({"exp":time.time() + config_token_expire_sec,"data":payload},config_key_jwt)
    return token

import jwt,json
async def function_token_decode(token,config_key_jwt):
    user=json.loads(jwt.decode(token,config_key_jwt,algorithms="HS256")["data"])
    return user

async def function_token_check(request,config_key_root,config_key_jwt):
    user={}
    api=request.url.path
    token=request.headers.get("Authorization").split("Bearer ",1)[1] if request.headers.get("Authorization") and request.headers.get("Authorization").startswith("Bearer ") else None
    if api.startswith("/root"):
        if token!=config_key_root:raise Exception("token root mismatch")
    else:
        if token:user=await function_token_decode(token,config_key_jwt)
        if api.startswith("/my") and not token:raise Exception("token missing")
        elif api.startswith("/private") and not token:raise Exception("token missing")
        elif api.startswith("/admin") and not token:raise Exception("token missing")
    return user

from openai import OpenAI
def function_client_read_gemini(config_gemini_key):
    client_gemini=OpenAI(api_key=config_gemini_key,base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    return client_gemini


#client
from databases import Database
async def function_client_read_postgres(config_postgres_url,config_postgres_min_connection=5,config_postgres_max_connection=20):
   client_postgres=Database(config_postgres_url,min_size=config_postgres_min_connection,max_size=config_postgres_max_connection)
   await client_postgres.connect()
   return client_postgres

async def function_object_create_postgres_asyncpg(client_postgres_asyncpg,table,object_dict):
    column_insert_list=list(object_dict.keys())
    query=f"""INSERT INTO {table} ({','.join(column_insert_list)}) VALUES ({','.join(['$'+str(i+1) for i in range(len(column_insert_list))])}) ON CONFLICT DO NOTHING;"""
    values=tuple(object_dict[col] for col in column_insert_list)
    await client_postgres_asyncpg.execute(query, *values)
    return None

def normalize_single_record(result, *, context: str = ""):
    if result is None:
        return None

    if isinstance(result, list):
        if not result:
            return None
        if len(result) > 1:
            raise Exception(
                f"Expected single row, got {len(result)} rows ({context})"
            )
        return result[0]

    return result

from io import BytesIO
import redis.asyncio as redis
def function_client_read_redis(config_redis_url):
    pool = redis.ConnectionPool.from_url(config_redis_url, decode_responses=True)
    client_redis = redis.Redis(connection_pool=pool)
    return client_redis