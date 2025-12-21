from controller.auth_controller import *
from schema.auth_model import *
from package import *
from main import *

@app.get("/")
async def function_api_root():
   return {"status":1,"message":"API is working!"}

@app.post("/auth/signup")
async def function_api_auth_signup(request:Request,signup:Signup):
   user=await function_auth_signup_username_password(request.app.state.client_postgres,signup.username,signup.password)
   print("checkpoint1")
   token = await function_token_encode(
      request.app.state.config_key_jwt,
      request.app.state.config_token_expire_sec,
      user,
      request.app.state.config_token_user_key_list
   )
   print("checkpoint2")
   return {"status":1,"message":token}

@app.post("/auth/login")
async def function_api_auth_login_password(request:Request,login:Login):
   user=await function_auth_login_username_password(request.app.state.client_postgres,login.username,login.password)
   token = await function_token_encode(
         request.app.state.config_key_jwt,
         request.app.state.config_token_expire_sec,
         user,
         request.app.state.config_token_user_key_list
      )
   return {"status":1,"message":token}