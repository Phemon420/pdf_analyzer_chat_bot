from package import *
from function import *
import os
import httpx
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/oauth/google/callback")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# All Google OAuth Scopes - Full permissions for Drive, Calendar, Gmail, Sheets
GOOGLE_SCOPES = [
    # Google Drive - Full access
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata",
    "https://www.googleapis.com/auth/drive.readonly",
    
    # Google Calendar - Full access
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.readonly",
    
    # Gmail - Full access
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    
    # User Profile
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


def get_google_auth_url(state: str = None) -> str:
    """
    Generate Google OAuth authorization URL with all required scopes.
    
    Args:
        state: Optional state parameter for CSRF protection (user_id or session_id)
    
    Returns:
        Full OAuth authorization URL
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",  # Required to get refresh_token
        "prompt": "consent",  # Force consent to always get refresh_token
        "include_granted_scopes": "true",
    }
    
    if state:
        params["state"] = state
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchange authorization code for access and refresh tokens.
    
    Args:
        code: Authorization code from OAuth callback
    
    Returns:
        Token response with access_token, refresh_token, expires_in, etc.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """
    Refresh an expired access token using the refresh token.
    
    Args:
        refresh_token: The stored refresh token
    
    Returns:
        New token response with access_token, expires_in, etc.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}")
        
        return response.json()


async def revoke_token(token: str) -> bool:
    """
    Revoke a Google OAuth token.
    
    Args:
        token: Access token or refresh token to revoke
    
    Returns:
        True if revocation successful
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_REVOKE_URL,
            params={"token": token},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        return response.status_code == 200


# Database operations for storing tokens

async def save_google_tokens(postgres_client, user_id: int, token_data: dict) -> dict:
    """
    Save or update Google OAuth tokens in the database.
    
    Args:
        postgres_client: Database client
        user_id: User ID to associate tokens with
        token_data: Token response from Google OAuth
    
    Returns:
        Saved token record
    """
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    token_type = token_data.get("token_type", "Bearer")
    scope = token_data.get("scope", "")
    
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    scopes_list = scope.split(" ") if scope else GOOGLE_SCOPES
    
    # Check if user already has tokens
    check_query = "SELECT id, refresh_token FROM google_tokens WHERE user_id = :user_id LIMIT 1;"
    existing = await postgres_client.fetch_all(query=check_query, values={"user_id": user_id})
    
    if existing:
        # Update existing tokens
        # Keep old refresh_token if new one not provided (refresh grants don't return new refresh_token)
        if not refresh_token:
            refresh_token = existing[0]["refresh_token"]
        
        update_query = """
            UPDATE google_tokens 
            SET access_token = :access_token, 
                refresh_token = :refresh_token,
                token_type = :token_type,
                expires_at = :expires_at,
                scopes = :scopes,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            RETURNING *;
        """
        values = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
            "scopes": scopes_list,
        }
        result = await postgres_client.fetch_all(query=update_query, values=values)
    else:
        # Insert new tokens
        insert_query = """
            INSERT INTO google_tokens (user_id, access_token, refresh_token, token_type, expires_at, scopes)
            VALUES (:user_id, :access_token, :refresh_token, :token_type, :expires_at, :scopes)
            RETURNING *;
        """
        values = {
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": token_type,
            "expires_at": expires_at,
            "scopes": scopes_list,
        }
        result = await postgres_client.fetch_all(query=insert_query, values=values)
    
    return result[0] if result else None


async def get_google_tokens(postgres_client, user_id: int) -> dict:
    """
    Get Google OAuth tokens for a user.
    Automatically refreshes if expired.
    
    Args:
        postgres_client: Database client
        user_id: User ID to get tokens for
    
    Returns:
        Token record with valid access_token, or None if not found
    """
    query = "SELECT * FROM google_tokens WHERE user_id = :user_id LIMIT 1;"
    result = await postgres_client.fetch_all(query=query, values={"user_id": user_id})
    
    if not result:
        return None
    
    token_record = dict(result[0])
    expires_at = token_record.get("expires_at")
    
    # Ensure expires_at is aware if it's naive from DB
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    # Check if token is expired (with 5 minute buffer)
    if expires_at and datetime.now(timezone.utc) >= (expires_at - timedelta(minutes=5)):
        try:
            # Refresh the token
            new_tokens = await refresh_access_token(token_record["refresh_token"])
            # Save new tokens
            updated_record = await save_google_tokens(postgres_client, user_id, new_tokens)
            return dict(updated_record) if updated_record else None
        except Exception as e:
            print(f"Failed to refresh token for user {user_id}: {e}")
            # If refresh fails, return current tokens anyway as last resort or return None?
            return token_record 
    
    return token_record


async def delete_google_tokens(postgres_client, user_id: int) -> bool:
    """
    Delete Google OAuth tokens for a user (revoke access).
    
    Args:
        postgres_client: Database client
        user_id: User ID to delete tokens for
    
    Returns:
        True if deleted successfully
    """
    # First get the tokens to revoke them
    tokens = await get_google_tokens(postgres_client, user_id)
    if tokens:
        # Revoke the refresh token (this invalidates all tokens)
        await revoke_token(tokens.get("refresh_token", ""))
    
    query = "DELETE FROM google_tokens WHERE user_id = :user_id;"
    await postgres_client.execute(query=query, values={"user_id": user_id})
    return True


async def check_google_connection_status(postgres_client, user_id: int) -> dict:
    """
    Check if user has valid Google OAuth connection and fetch user info.
    """
    tokens = await get_google_tokens(postgres_client, user_id)
    
    if not tokens:
        return {"connected": False}
    
    user_info = {}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            if resp.status_code == 200:
                user_info = resp.json()
    except Exception as e:
        print(f"Failed to fetch user info: {e}")
    
    return {
        "connected": True,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "expires_at": tokens.get("expires_at").isoformat() if tokens.get("expires_at") else None,
        "scopes": tokens.get("scopes", []),
    }
