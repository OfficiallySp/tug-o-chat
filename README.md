# Tug-o-Chat - Twitch Tug of War Game

A real-time multiplayer tug of war game where Twitch streamers compete against each other, with their viewers helping by spamming `!PULL` in chat.

## Features

- **Twitch OAuth Integration**: Streamers login with their Twitch account
- **Random Matchmaking**: Automatically pairs streamers for battles
- **Chat Integration**: Monitors Twitch chat for `!PULL` commands
- **Fair Balancing System**: Uses engagement rate instead of raw viewer count
- **Real-time Updates**: WebSocket connection for instant game updates
- **Beautiful UI**: Modern, Twitch-themed interface with Canvas animations

## How It Works

1. Streamers login with their Twitch account
2. They join the matchmaking queue
3. Once matched, both streamers' chats are monitored
4. Viewers type `!PULL` to help their streamer
5. The game uses an **engagement-based algorithm** to ensure fairness:
   - Measures unique pullers per 30-second window
   - Calculates engagement rate (active viewers / total viewers)
   - Uses logarithmic scaling to balance different viewer counts

## Setup Instructions

### Prerequisites

- Python 3.8+
- Twitch Developer Application

### 1. Create a Twitch Application

1. Go to [Twitch Developer Console](https://dev.twitch.tv/console)
2. Click "Register Your Application"
3. Set OAuth Redirect URL to: `http://localhost:3000/auth/callback`
4. Note your Client ID and Client Secret

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
copy .env.example .env
# Edit .env and add your Twitch credentials

# Run the server
python main.py
```

### 3. Frontend Setup

The frontend is static HTML/CSS/JS, so you just need to serve it:

```bash
cd frontend

# Using Python's built-in server
python -m http.server 3000

# Or using Node.js http-server
npx http-server -p 3000

# Or any other static file server
```

### 4. Access the Game

1. Open http://localhost:3000 in your browser
2. Click "Login with Twitch"
3. Authorize the application
4. Start playing!

## Game Balance Algorithm

The game uses an engagement-based system to ensure fairness:

```python
# Calculate engagement rate
engagement_rate = unique_pullers_in_30s / total_viewers
pull_power = engagement_rate * base_strength * log(unique_pullers + 1)
```

This means:
- A streamer with 100 viewers and 20 unique pullers
- Has similar power to a streamer with 1000 viewers and 50 unique pullers
- It rewards community engagement over raw numbers

## Project Structure

```
tug-o-chat/
├── backend/
│   ├── main.py              # FastAPI server & WebSocket handling
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models
│   ├── twitch_auth.py       # Twitch OAuth handling
│   ├── twitch_chat.py       # Chat monitoring with TwitchIO
│   ├── game_manager.py      # Game logic & balancing
│   ├── matchmaking.py       # Player matchmaking system
│   └── requirements.txt     # Python dependencies
└── frontend/
    ├── index.html           # Main HTML file
    ├── style.css            # Styling
    └── script.js            # Client-side logic
```

## Deployment

For production deployment:

1. **Update CORS settings** in `backend/main.py`
2. **Use HTTPS** for both frontend and backend
3. **Update Twitch OAuth redirect URL** in both Twitch console and `.env`
4. **Consider using Redis** for scaling to multiple servers
5. **Use a process manager** like PM2 or systemd for the backend

### Recommended Hosting:

- **Backend**: Heroku, Railway, or Render
- **Frontend**: Netlify, Vercel, or GitHub Pages

## Environment Variables

Create a `.env` file in the backend directory:

```env
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
TWITCH_REDIRECT_URI=http://localhost:3000/auth/callback
SECRET_KEY=generate-a-random-secret-key
```

## Troubleshooting

### WebSocket Connection Issues
- Make sure both frontend and backend are running
- Check that ports 3000 and 8000 are not blocked
- Verify CORS settings if deploying

### Twitch OAuth Issues
- Ensure redirect URI matches exactly in Twitch console
- Check that client ID and secret are correct
- Verify scopes include chat:read

### Chat Monitoring Not Working
- Streamer must be live for viewer count
- Bot needs to join the channel (happens automatically)
- Check TwitchIO connection in backend logs

## License

MIT License - feel free to modify and use for your own projects!

## Contributing

Pull requests are welcome! For major changes, please open an issue first.
