from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
import uuid


class GameStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class Player(BaseModel):
    id: str = ""
    username: str
    channel_name: str
    access_token: str
    viewer_count: int = 0
    session_id: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())


class PullData(BaseModel):
    timestamp: datetime
    username: str
    player_id: str


class GameRoom(BaseModel):
    id: str
    player1: Player
    player2: Player
    status: GameStatus = GameStatus.WAITING
    rope_position: float = 0.0  # -100 to 100, 0 is center
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    winner_id: Optional[str] = None
    pull_history: List[PullData] = []
    player1_stats: Dict[str, float] = {}
    player2_stats: Dict[str, float] = {}

    def __init__(self, **data):
        super().__init__(**data)
        if not self.id:
            self.id = str(uuid.uuid4())


class GameState(BaseModel):
    room_id: str
    rope_position: float
    player1_score: int
    player2_score: int
    time_remaining: int
    status: GameStatus
    player1_engagement: float
    player2_engagement: float


class QueuePlayer(BaseModel):
    player: Player
    joined_at: datetime
    session_id: str
