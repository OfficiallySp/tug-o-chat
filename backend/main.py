from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from typing import Dict, Optional
import json
import logging

from config import settings
from models import GameState, Player, GameRoom
from twitch_auth import twitch_auth_router
from twitch_chat import TwitchChatMonitor
from game_manager import GameManager
from matchmaking import MatchmakingQueue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
game_manager = GameManager()
matchmaking_queue = MatchmakingQueue()
chat_monitors: Dict[str, TwitchChatMonitor] = {}
connected_websockets: Dict[str, WebSocket] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Tug-o-Chat server...")
    # Start background tasks
    asyncio.create_task(game_manager.game_loop())
    asyncio.create_task(matchmaking_queue.process_queue())
    yield
    # Shutdown
    logger.info("Shutting down Tug-o-Chat server...")
    # Clean up all chat monitors
    for monitor in chat_monitors.values():
        await monitor.stop()


app = FastAPI(title="Tug-o-Chat", lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(twitch_auth_router, prefix="/api/auth")


@app.get("/")
async def root():
    return {"message": "Tug-o-Chat API is running!"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    connected_websockets[session_id] = websocket

    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(session_id, data)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        await handle_disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await handle_disconnect(session_id)
    finally:
        if session_id in connected_websockets:
            del connected_websockets[session_id]


async def handle_websocket_message(session_id: str, data: dict):
    """Handle incoming WebSocket messages from clients"""
    msg_type = data.get("type")

    if msg_type == "join_queue":
        player_data = data.get("player")
        if player_data:
            player = Player(**player_data)
            player.session_id = session_id
            await matchmaking_queue.add_player(player)
            await send_to_client(session_id, {
                "type": "queue_joined",
                "message": "You've joined the matchmaking queue!"
            })

    elif msg_type == "leave_queue":
        await matchmaking_queue.remove_player(session_id)
        await send_to_client(session_id, {
            "type": "queue_left",
            "message": "You've left the matchmaking queue."
        })

    elif msg_type == "game_ready":
        room_id = data.get("room_id")
        if room_id:
            room = game_manager.get_room(room_id)
            if room and session_id in [room.player1.session_id, room.player2.session_id]:
                # Start monitoring chat for this player
                player = room.player1 if room.player1.session_id == session_id else room.player2
                await start_chat_monitoring(player, room_id)


async def handle_disconnect(session_id: str):
    """Handle player disconnection"""
    # Remove from matchmaking queue
    await matchmaking_queue.remove_player(session_id)

    # Handle game disconnection
    room = game_manager.get_room_by_session(session_id)
    if room:
        await game_manager.handle_player_disconnect(room.id, session_id)

        # Stop chat monitoring
        if session_id in chat_monitors:
            await chat_monitors[session_id].stop()
            del chat_monitors[session_id]


async def start_chat_monitoring(player: Player, room_id: str):
    """Start monitoring Twitch chat for a player"""
    if player.session_id in chat_monitors:
        await chat_monitors[player.session_id].stop()

    monitor = TwitchChatMonitor(
        channel=player.channel_name,
        access_token=player.access_token,
        room_id=room_id,
        player_id=player.id,
        on_pull_command=handle_pull_command
    )

    chat_monitors[player.session_id] = monitor
    asyncio.create_task(monitor.start())


async def handle_pull_command(room_id: str, player_id: str, username: str):
    """Handle !PULL command from chat"""
    await game_manager.register_pull(room_id, player_id, username)


async def send_to_client(session_id: str, data: dict):
    """Send data to a specific client via WebSocket"""
    if session_id in connected_websockets:
        try:
            await connected_websockets[session_id].send_json(data)
        except Exception as e:
            logger.error(f"Error sending to client {session_id}: {e}")


async def broadcast_to_room(room_id: str, data: dict):
    """Broadcast data to all players in a room"""
    room = game_manager.get_room(room_id)
    if room:
        for player in [room.player1, room.player2]:
            if player and player.session_id:
                await send_to_client(player.session_id, data)


# Export functions for use in other modules
app.send_to_client = send_to_client
app.broadcast_to_room = broadcast_to_room


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
