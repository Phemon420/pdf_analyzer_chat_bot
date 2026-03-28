import os
import json
import httpx
from datetime import datetime
from typing import Dict, Any

async def get_current_time(db, user_id: int, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Get the current date and time for a specific timezone using World Time API."""
    timezone = parameters.get("timezone", "Asia/Kolkata")
    api_key = os.getenv("timezone_api_key")
    if not api_key:
        return {"status": "error", "message": "API key 'timezone_api_key' not found in environment"}
        
    url = f"https://world-time-api3.p.rapidapi.com/timezone/{timezone}"
    headers = {
        "x-api-host": "world-time-api3.p.rapidapi.com",
        "x-api-key": api_key
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                try:
                    return {"status": "success", "data": response.json()}
                except:
                    return {"status": "success", "data": response.text}
            else:
                return {"status": "error", "message": f"API returned status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
