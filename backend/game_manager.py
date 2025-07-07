import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
import math
import logging

from models import GameRoom, GameStatus, PullData, GameState
from config import settings

logger = logging.getLogger(__name__)


class GameManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.session_to_room: Dict[str, str] = {}

    def create_room(self, player1, player2) -> GameRoom:
        """Create a new game room"""
        room = GameRoom(
            id="",  # Will be auto-generated
            player1=player1,
            player2=player2,
            status=GameStatus.WAITING
        )
        self.rooms[room.id] = room
        self.session_to_room[player1.session_id] = room.id
        self.session_to_room[player2.session_id] = room.id
        return room

    def get_room(self, room_id: str) -> Optional[GameRoom]:
        """Get a room by ID"""
        return self.rooms.get(room_id)

    def get_room_by_session(self, session_id: str) -> Optional[GameRoom]:
        """Get a room by player session ID"""
        room_id = self.session_to_room.get(session_id)
        return self.get_room(room_id) if room_id else None

    async def start_game(self, room_id: str):
        """Start a game in a room"""
        room = self.get_room(room_id)
        if not room or room.status != GameStatus.WAITING:
            return

        room.status = GameStatus.ACTIVE
        room.start_time = datetime.now()
        room.rope_position = 0.0

        # Initialize stats
        room.player1_stats = {
            "total_pulls": 0,
            "unique_pullers": 0,
            "engagement_rate": 0.0,
            "pull_power": 0.0
        }
        room.player2_stats = room.player1_stats.copy()

        logger.info(f"Game started in room {room_id}")

    async def register_pull(self, room_id: str, player_id: str, username: str):
        """Register a pull command from a viewer"""
        room = self.get_room(room_id)
        if not room or room.status != GameStatus.ACTIVE:
            return

        # Add to pull history
        pull = PullData(
            timestamp=datetime.now(),
            username=username,
            player_id=player_id
        )
        room.pull_history.append(pull)

        # Update stats based on which player
        if player_id == room.player1.id:
            room.player1_stats["total_pulls"] += 1
        else:
            room.player2_stats["total_pulls"] += 1

    def calculate_engagement_stats(self, room: GameRoom):
        """Calculate engagement-based statistics for balancing"""
        now = datetime.now()
        window = timedelta(seconds=30)  # 30-second window

        # Get pulls in the last window
        recent_pulls = [p for p in room.pull_history if now - p.timestamp < window]

        # Calculate for player 1
        p1_pulls = [p for p in recent_pulls if p.player_id == room.player1.id]
        p1_unique = len(set(p.username for p in p1_pulls))
        p1_engagement = p1_unique / max(room.player1.viewer_count, 1)

        # Calculate for player 2
        p2_pulls = [p for p in recent_pulls if p.player_id == room.player2.id]
        p2_unique = len(set(p.username for p in p2_pulls))
        p2_engagement = p2_unique / max(room.player2.viewer_count, 1)

        # Update stats
        room.player1_stats["unique_pullers"] = p1_unique
        room.player1_stats["engagement_rate"] = p1_engagement
        room.player2_stats["unique_pullers"] = p2_unique
        room.player2_stats["engagement_rate"] = p2_engagement

        # Calculate pull power with logarithmic scaling
        base_power = settings.base_pull_strength
        room.player1_stats["pull_power"] = p1_engagement * base_power * math.log10(p1_unique + 1)
        room.player2_stats["pull_power"] = p2_engagement * base_power * math.log10(p2_unique + 1)

    def update_rope_position(self, room: GameRoom):
        """Update the rope position based on pull powers"""
        if room.status != GameStatus.ACTIVE:
            return

        # Calculate engagement stats first
        self.calculate_engagement_stats(room)

        # Get pull powers
        p1_power = room.player1_stats["pull_power"]
        p2_power = room.player2_stats["pull_power"]

        # Calculate net force
        net_force = p1_power - p2_power

        # Update rope position (with some dampening)
        room.rope_position += net_force * 0.5

        # Clamp to bounds
        room.rope_position = max(-settings.win_threshold,
                                min(settings.win_threshold, room.rope_position))

        # Check win condition
        if abs(room.rope_position) >= settings.win_threshold:
            asyncio.create_task(self.end_game(room.id))

    async def end_game(self, room_id: str):
        """End a game"""
        room = self.get_room(room_id)
        if not room:
            return

        room.status = GameStatus.FINISHED
        room.end_time = datetime.now()

        # Determine winner
        if room.rope_position <= -settings.win_threshold:
            room.winner_id = room.player2.id
        elif room.rope_position >= settings.win_threshold:
            room.winner_id = room.player1.id

        logger.info(f"Game ended in room {room_id}, winner: {room.winner_id}")

        # Clean up after a delay
        await asyncio.sleep(30)
        self.cleanup_room(room_id)

    def cleanup_room(self, room_id: str):
        """Clean up a room"""
        room = self.get_room(room_id)
        if room:
            # Remove session mappings
            if room.player1.session_id in self.session_to_room:
                del self.session_to_room[room.player1.session_id]
            if room.player2.session_id in self.session_to_room:
                del self.session_to_room[room.player2.session_id]

        # Remove room
        if room_id in self.rooms:
            del self.rooms[room_id]

    async def handle_player_disconnect(self, room_id: str, session_id: str):
        """Handle a player disconnecting"""
        room = self.get_room(room_id)
        if not room:
            return

        if room.status == GameStatus.ACTIVE:
            room.status = GameStatus.ABANDONED
            # The other player wins by default
            if room.player1.session_id == session_id:
                room.winner_id = room.player2.id
            else:
                room.winner_id = room.player1.id

        await self.end_game(room_id)

    def get_game_state(self, room_id: str) -> Optional[GameState]:
        """Get the current game state"""
        room = self.get_room(room_id)
        if not room:
            return None

        time_remaining = 0
        if room.start_time and room.status == GameStatus.ACTIVE:
            elapsed = (datetime.now() - room.start_time).total_seconds()
            time_remaining = max(0, settings.game_duration - elapsed)

        return GameState(
            room_id=room_id,
            rope_position=room.rope_position,
            player1_score=int(room.player1_stats.get("unique_pullers", 0)),
            player2_score=int(room.player2_stats.get("unique_pullers", 0)),
            time_remaining=int(time_remaining),
            status=room.status,
            player1_engagement=room.player1_stats.get("engagement_rate", 0),
            player2_engagement=room.player2_stats.get("engagement_rate", 0)
        )

    async def game_loop(self):
        """Main game loop that updates all active games"""
        while True:
            try:
                # Update all active games
                active_rooms = [r for r in self.rooms.values()
                              if r.status == GameStatus.ACTIVE]

                for room in active_rooms:
                    # Update rope position
                    self.update_rope_position(room)

                    # Check time limit
                    if room.start_time:
                        elapsed = (datetime.now() - room.start_time).total_seconds()
                        if elapsed >= settings.game_duration:
                            await self.end_game(room.id)
                            continue

                    # Broadcast game state
                    state = self.get_game_state(room.id)
                    if state:
                        # This will be sent via WebSocket in main.py
                        from main import app
                        await app.broadcast_to_room(room.id, {
                            "type": "game_update",
                            "state": state.dict()
                        })

            except Exception as e:
                logger.error(f"Error in game loop: {e}")

            await asyncio.sleep(0.1)  # Update 10 times per second
