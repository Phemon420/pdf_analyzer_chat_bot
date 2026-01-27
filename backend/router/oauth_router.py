from package import *
from controller.oauth_controller import (
    get_google_auth_url,
    exchange_code_for_tokens,
    save_google_tokens,
    get_google_tokens,
    delete_google_tokens,
    check_google_connection_status,
    refresh_access_token,
    FRONTEND_URL
)
import os

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@router.get("/oauth/google/url")
async def get_oauth_url(request: Request):
    """
    Get Google OAuth authorization URL.
    User must be authenticated to use this endpoint.
    """
    user = request.state.user
    if not user or not user.get("id"):
        return {"status": 0, "message": "Authentication required"}
    
    # Use user ID as state for security
    state = str(user["id"])
    auth_url = get_google_auth_url(state=state)
    
    return {"status": 1, "url": auth_url}


@router.get("/oauth/google/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    This is called by Google after user grants/denies permission.
    """
    # Handle error from Google
    if error:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/oauth/callback?error={error}",
            status_code=302
        )
    
    if not code:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/oauth/callback?error=no_code",
            status_code=302
        )
    
    try:
        # Exchange code for tokens
        token_data = await exchange_code_for_tokens(code)
        
        # Get user ID from state parameter
        user_id = int(state) if state else None
        
        if not user_id:
            return RedirectResponse(
                url=f"{FRONTEND_URL}/oauth/callback?error=invalid_state",
                status_code=302
            )
        
        # Save tokens to database
        postgres_client = request.app.state.client_postgres
        await save_google_tokens(postgres_client, user_id, token_data)
        
        # Redirect to frontend success page
        return RedirectResponse(
            url=f"{FRONTEND_URL}/oauth/callback?success=true",
            status_code=302
        )
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/oauth/callback?error={str(e)}",
            status_code=302
        )


@router.get("/oauth/google/status")
async def get_oauth_status(request: Request):
    """
    Get Google OAuth connection status for the current user.
    Returns whether the user has connected their Google account.
    """
    user = request.state.user
    if not user or not user.get("id"):
        return {"status": 0, "message": "Authentication required"}
    
    try:
        postgres_client = request.app.state.client_postgres
        connection_status = await check_google_connection_status(postgres_client, user["id"])
        
        return {"status": 1, **connection_status}
    except Exception as e:
        print(f"Error checking OAuth status: {e}")
        return {"status": 0, "message": str(e)}


@router.post("/oauth/google/refresh")
async def refresh_oauth_token(request: Request):
    """
    Manually refresh the Google OAuth access token.
    """
    user = request.state.user
    if not user or not user.get("id"):
        return {"status": 0, "message": "Authentication required"}
    
    try:
        postgres_client = request.app.state.client_postgres
        
        # Get current tokens
        tokens = await get_google_tokens(postgres_client, user["id"])
        if not tokens:
            return {"status": 0, "message": "No Google connection found"}
        
        # Refresh the token
        new_token_data = await refresh_access_token(tokens["refresh_token"])
        
        # Save updated tokens
        await save_google_tokens(postgres_client, user["id"], new_token_data)
        
        return {"status": 1, "message": "Token refreshed successfully"}
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return {"status": 0, "message": str(e)}


@router.post("/oauth/google/revoke")
async def revoke_oauth_token(request: Request):
    """
    Revoke Google OAuth access and delete stored tokens.
    """
    user = request.state.user
    if not user or not user.get("id"):
        return {"status": 0, "message": "Authentication required"}
    
    try:
        postgres_client = request.app.state.client_postgres
        await delete_google_tokens(postgres_client, user["id"])
        
        return {"status": 1, "message": "Google access revoked successfully"}
    except Exception as e:
        print(f"Error revoking token: {e}")
        return {"status": 0, "message": str(e)}


@router.get("/oauth/google/tokens")
async def get_user_tokens(request: Request):
    """
    Get the current user's Google OAuth tokens (for internal use/tools).
    Returns access token that can be used to call Google APIs.
    """
    user = request.state.user
    if not user or not user.get("id"):
        return {"status": 0, "message": "Authentication required"}
    
    try:
        postgres_client = request.app.state.client_postgres
        tokens = await get_google_tokens(postgres_client, user["id"])
        
        if not tokens:
            return {"status": 0, "message": "No Google connection found", "connected": False}
        
        return {
            "status": 1,
            "connected": True,
            "access_token": tokens["access_token"],
            "token_type": tokens["token_type"],
            "expires_at": tokens["expires_at"].isoformat() if tokens.get("expires_at") else None,
        }
    except Exception as e:
        print(f"Error getting tokens: {e}")
        return {"status": 0, "message": str(e)}
