import asyncio
from datetime import datetime
from typing import Dict, Optional, List
import logging
import random

from models import Player, QueuePlayer, GameRoom
from game_manager import GameManager

logger = logging.getLogger(__name__)


class MatchmakingQueue:
    def __init__(self):
        self.queue: List[QueuePlayer] = []
        self.queue_lock = asyncio.Lock()

    async def add_player(self, player: Player):
        """Add a player to the matchmaking queue"""
        async with self.queue_lock:
            # Check if player is already in queue
            for q_player in self.queue:
                if q_player.session_id == player.session_id:
                    logger.info(f"Player {player.username} already in queue")
                    return

            if not player.session_id:
                logger.error(f"Player {player.username} has no session_id")
                return

            queue_player = QueuePlayer(
                player=player,
                joined_at=datetime.now(),
                session_id=player.session_id
            )
            self.queue.append(queue_player)
            logger.info(f"Player {player.username} joined matchmaking queue")

    async def remove_player(self, session_id: str):
        """Remove a player from the queue"""
        async with self.queue_lock:
            self.queue = [p for p in self.queue if p.session_id != session_id]

    async def find_match(self) -> Optional[tuple[Player, Player]]:
        """Try to find a match between two players"""
        async with self.queue_lock:
            if len(self.queue) < 2:
                return None

            # Simple matchmaking: pair the first two players
            # In a more advanced system, you could match by viewer count ranges
            player1 = self.queue.pop(0)
            player2 = self.queue.pop(0)

            return (player1.player, player2.player)

    async def process_queue(self):
        """Background task to process the matchmaking queue"""
        from main import app, game_manager

        while True:
            try:
                match = await self.find_match()
                if match:
                    player1, player2 = match

                    # Create game room
                    room = game_manager.create_room(player1, player2)

                    # Notify both players
                    match_data = {
                        "type": "match_found",
                        "room_id": room.id,
                        "opponent": {
                            "username": player2.username,
                            "channel_name": player2.channel_name,
                            "viewer_count": player2.viewer_count
                        }
                    }
                    await app.send_to_client(player1.session_id, match_data)

                    match_data["opponent"] = {
                        "username": player1.username,
                        "channel_name": player1.channel_name,
                        "viewer_count": player1.viewer_count
                    }
                    await app.send_to_client(player2.session_id, match_data)

                    # Start game after a short delay
                    await asyncio.sleep(5)
                    await game_manager.start_game(room.id)

                    # Notify game started
                    await app.broadcast_to_room(room.id, {
                        "type": "game_started",
                        "message": "The tug of war has begun! Chat, type !PULL to help!"
                    })

            except Exception as e:
                logger.error(f"Error in matchmaking process: {e}")

            await asyncio.sleep(1)  # Check for matches every second
