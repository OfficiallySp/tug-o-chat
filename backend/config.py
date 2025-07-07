from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Twitch OAuth settings
    twitch_client_id: str
    twitch_client_secret: str
    twitch_redirect_uri: str = "http://localhost:3000/auth/callback"

    # Server settings
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Game settings
    game_duration: int = 120  # seconds
    pull_cooldown: float = 0.5  # seconds between pulls per user
    base_pull_strength: float = 1.0
    win_threshold: float = 100.0  # Distance to win

    # Redis settings (optional, for scaling)
    redis_url: Optional[str] = None

    # Security
    secret_key: str = "your-secret-key-here"  # Change in production

    class Config:
        env_file = ".env"


settings = Settings()
