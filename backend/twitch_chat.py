import asyncio
from twitchio.ext import commands
from typing import Callable, Set, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TwitchChatMonitor:
    def __init__(self, channel: str, access_token: str, room_id: str, player_id: str,
                 on_pull_command: Callable):
        self.channel = channel
        self.access_token = access_token
        self.room_id = room_id
        self.player_id = player_id
        self.on_pull_command = on_pull_command
        self.bot = None
        self._running = False

        # Track users and cooldowns
        self.user_cooldowns: Dict[str, datetime] = {}
        self.cooldown_seconds = 0.5  # Time between pulls per user

    async def start(self):
        """Start monitoring the Twitch chat"""
        if self._running:
            return

        self._running = True

        # Create bot instance
        self.bot = Bot(
            token=self.access_token,
            prefix='!',
            initial_channels=[self.channel],
            chat_monitor=self
        )

        try:
            await self.bot.start()
        except Exception as e:
            logger.error(f"Error starting chat monitor for {self.channel}: {e}")
            self._running = False

    async def stop(self):
        """Stop monitoring the chat"""
        self._running = False
        if self.bot:
            await self.bot.close()

    def can_pull(self, username: str) -> bool:
        """Check if a user can pull (cooldown check)"""
        now = datetime.now()

        if username in self.user_cooldowns:
            last_pull = self.user_cooldowns[username]
            if now - last_pull < timedelta(seconds=self.cooldown_seconds):
                return False

        self.user_cooldowns[username] = now
        return True

    async def handle_pull(self, username: str):
        """Handle a pull command from a user"""
        if self.can_pull(username):
            await self.on_pull_command(self.room_id, self.player_id, username)


class Bot(commands.Bot):
    def __init__(self, token, prefix, initial_channels, chat_monitor):
        super().__init__(token=token, prefix=prefix, initial_channels=initial_channels)
        self.chat_monitor = chat_monitor

    async def event_ready(self):
        logger.info(f'Logged in as | {self.nick}')
        logger.info(f'User id is | {self.user_id}')

    async def event_message(self, message):
        # Ignore messages from the bot itself
        if message.echo:
            return

        # Process commands
        await self.handle_commands(message)

    @commands.command(name='pull', aliases=['PULL', 'Pull'])
    async def pull_command(self, ctx: commands.Context):
        """Handle the !pull command"""
        await self.chat_monitor.handle_pull(ctx.author.name)
