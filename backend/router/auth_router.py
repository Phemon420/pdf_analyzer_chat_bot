from package import *
from controller.auth_controller import *
from controller.oauth_controller import check_google_connection_status
from schema.auth_model import *
from fastapi import Request

@router.get("/")
async def function_api_root():
   return {"status":1,"message":"API is working!"}

@router.post("/auth/signup")
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
   return {"status":1,"Token":token}

@router.post("/auth/login")
async def function_api_auth_login_password(request:Request,login:Login):
   user = await function_auth_login_username_password(request.app.state.client_postgres, login.username, login.password)
   if not user:
       return {"status": 0, "message": "Invalid username or password"}
       
   token = await function_token_encode(
         request.app.state.config_key_jwt,
         request.app.state.config_token_expire_sec,
         user,
         request.app.state.config_token_user_key_list
      )
   return {"status":1,"Token":token}

@router.get("/auth/me")
async def get_current_user(request: Request):
   user = request.state.user
   if not user or not user.get("id"):
      return {"status": 0, "message": "Authentication required"}

   postgres_client = request.app.state.client_postgres
   google_status = await check_google_connection_status(postgres_client, user["id"])

   return {
      "status": 1,
      "user": {
         "id": user["id"],
         "username": user["username"],
      },
      "google": google_status
   }