from package import *
from function import *

import hashlib
async def function_auth_signup_username_password(postgres_client,username,password):
    query="insert into users (username,password) values (:username,:password) returning *;" 
    values={"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
    output=await postgres_client.fetch_all(query=query,values=values)
    # print(output[0])
    user = normalize_single_record(output, context="signup")
    print(user)
    return user

async def function_auth_login_username_password(postgres_client,username,password):
    query=f"select * from users where username=:username and password=:password order by id desc limit 1;"
    values={"username":username,"password":hashlib.sha256(str(password).encode()).hexdigest()}
    output=await postgres_client.fetch_all(query=query,values=values)
    user = normalize_single_record(output, context="login")
    return user