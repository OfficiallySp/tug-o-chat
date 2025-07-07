from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import httpx
import secrets
import logging
from typing import Optional
from urllib.parse import urlencode

from config import settings

logger = logging.getLogger(__name__)

twitch_auth_router = APIRouter()

# Store state tokens temporarily (in production, use Redis or similar)
state_tokens = {}


@twitch_auth_router.get("/login")
async def twitch_login():
    """Initiate Twitch OAuth flow"""
    state = secrets.token_urlsafe(32)
    state_tokens[state] = True

    params = {
        "client_id": settings.twitch_client_id,
        "redirect_uri": settings.twitch_redirect_uri,
        "response_type": "code",
        "scope": "user:read:email channel:read:subscriptions chat:read",
        "state": state
    }

    auth_url = f"https://id.twitch.tv/oauth2/authorize?{urlencode(params)}"
    return {"auth_url": auth_url}


@twitch_auth_router.get("/callback")
async def twitch_callback(code: str = Query(...), state: str = Query(...)):
    """Handle Twitch OAuth callback"""
    # Verify state token
    if state not in state_tokens:
        raise HTTPException(status_code=400, detail="Invalid state token")

    del state_tokens[state]

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": settings.twitch_client_id,
                "client_secret": settings.twitch_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.twitch_redirect_uri
            }
        )

        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get access token")

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://api.twitch.tv/helix/users",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Client-Id": settings.twitch_client_id
            }
        )

        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        user_data = user_response.json()["data"][0]

        # Get channel info for viewer count
        channel_response = await client.get(
            f"https://api.twitch.tv/helix/streams?user_id={user_data['id']}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Client-Id": settings.twitch_client_id
            }
        )

        viewer_count = 0
        if channel_response.status_code == 200:
            streams = channel_response.json()["data"]
            if streams:
                viewer_count = streams[0]["viewer_count"]

        # Return user data to frontend
        return {
            "user": {
                "id": user_data["id"],
                "username": user_data["display_name"],
                "channel_name": user_data["login"],
                "profile_image": user_data["profile_image_url"],
                "viewer_count": viewer_count
            },
            "access_token": access_token
        }


@twitch_auth_router.get("/validate")
async def validate_token(access_token: str):
    """Validate a Twitch access token"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={"Authorization": f"OAuth {access_token}"}
        )

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid access token")

        return {"valid": True, "data": response.json()}
