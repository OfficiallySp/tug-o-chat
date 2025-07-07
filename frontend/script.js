// Configuration
const BACKEND_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000';

// Game state
let currentUser = null;
let currentRoom = null;
let ws = null;
let sessionId = null;
let gameCanvas = null;
let gameCtx = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Generate session ID
    sessionId = generateSessionId();

    // Initialize canvas
    gameCanvas = document.getElementById('game-canvas');
    gameCtx = gameCanvas.getContext('2d');

    // Check if returning from Twitch OAuth
    handleOAuthCallback();

    // Setup event listeners
    setupEventListeners();
});

function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9);
}

function setupEventListeners() {
    // Login button
    document.getElementById('twitch-login-btn').addEventListener('click', async () => {
        try {
            const response = await fetch(`${BACKEND_URL}/api/auth/login`);
            const data = await response.json();
            if (data.auth_url) {
                window.location.href = data.auth_url;
            }
        } catch (error) {
            console.error('Failed to get auth URL:', error);
            alert('Failed to connect to server');
        }
    });

    // Find match button
    document.getElementById('find-match-btn').addEventListener('click', joinQueue);

    // Cancel queue button
    document.getElementById('cancel-queue-btn').addEventListener('click', leaveQueue);

    // Play again button
    document.getElementById('play-again-btn').addEventListener('click', () => {
        showScreen('lobby-screen');
    });
}

async function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');

    if (code && state) {
        try {
            const response = await fetch(`${BACKEND_URL}/api/auth/callback?code=${code}&state=${state}`);
            const data = await response.json();

            if (data.user && data.access_token) {
                currentUser = {
                    ...data.user,
                    access_token: data.access_token
                };

                // Clear URL parameters
                window.history.replaceState({}, document.title, window.location.pathname);

                // Connect WebSocket
                connectWebSocket();

                // Show lobby
                showLobby();
            }
        } catch (error) {
            console.error('OAuth callback error:', error);
            alert('Failed to authenticate with Twitch');
        }
    }
}

function connectWebSocket() {
    ws = new WebSocket(`${WS_URL}/ws/${sessionId}`);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'queue_joined':
            document.getElementById('queue-status').classList.remove('hidden');
            document.getElementById('find-match-btn').classList.add('hidden');
            document.getElementById('cancel-queue-btn').classList.remove('hidden');
            break;

        case 'queue_left':
            document.getElementById('queue-status').classList.add('hidden');
            document.getElementById('find-match-btn').classList.remove('hidden');
            document.getElementById('cancel-queue-btn').classList.add('hidden');
            break;

        case 'match_found':
            currentRoom = data.room_id;
            showGame(data.opponent);
            // Notify server we're ready
            ws.send(JSON.stringify({
                type: 'game_ready',
                room_id: currentRoom
            }));
            break;

        case 'game_started':
            console.log('Game started!');
            break;

        case 'game_update':
            updateGame(data.state);
            break;

        case 'game_ended':
            showResult(data.winner, data.stats);
            break;
    }
}

function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

function showLobby() {
    // Update player info
    document.getElementById('player-avatar').src = currentUser.profile_image;
    document.getElementById('player-name').textContent = currentUser.username;
    document.getElementById('viewer-count').textContent = currentUser.viewer_count;

    showScreen('lobby-screen');
}

function joinQueue() {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        alert('Connection lost. Please refresh the page.');
        return;
    }

    ws.send(JSON.stringify({
        type: 'join_queue',
        player: currentUser
    }));
}

function leaveQueue() {
    ws.send(JSON.stringify({
        type: 'leave_queue'
    }));
}

function showGame(opponent) {
    // Set player info
    document.getElementById('player1-avatar').src = currentUser.profile_image;
    document.getElementById('player1-name').textContent = currentUser.username;

    document.getElementById('player2-avatar').src = opponent.profile_image || 'https://via.placeholder.com/60';
    document.getElementById('player2-name').textContent = opponent.username;

    showScreen('game-screen');

    // Initialize game canvas
    initializeGameCanvas();
}

function initializeGameCanvas() {
    // Set canvas size
    const container = gameCanvas.parentElement;
    gameCanvas.width = Math.min(800, container.clientWidth - 40);
    gameCanvas.height = 400;

    // Initial draw
    drawGame(0);
}

function drawGame(ropePosition) {
    const width = gameCanvas.width;
    const height = gameCanvas.height;
    const centerX = width / 2;
    const centerY = height / 2;

    // Clear canvas
    gameCtx.clearRect(0, 0, width, height);

    // Draw background
    gameCtx.fillStyle = '#0e0e10';
    gameCtx.fillRect(0, 0, width, height);

    // Draw center line
    gameCtx.strokeStyle = '#464649';
    gameCtx.lineWidth = 2;
    gameCtx.setLineDash([10, 10]);
    gameCtx.beginPath();
    gameCtx.moveTo(centerX, 0);
    gameCtx.lineTo(centerX, height);
    gameCtx.stroke();
    gameCtx.setLineDash([]);

    // Draw win zones
    const winZoneWidth = width * 0.1;

    // Left win zone (player 2 wins)
    gameCtx.fillStyle = 'rgba(255, 107, 107, 0.2)';
    gameCtx.fillRect(0, 0, winZoneWidth, height);

    // Right win zone (player 1 wins)
    gameCtx.fillStyle = 'rgba(145, 70, 255, 0.2)';
    gameCtx.fillRect(width - winZoneWidth, 0, winZoneWidth, height);

    // Calculate rope position
    const ropeX = centerX + (ropePosition / 100) * (width / 2 - winZoneWidth);

    // Draw rope
    gameCtx.strokeStyle = '#d4a373';
    gameCtx.lineWidth = 20;
    gameCtx.lineCap = 'round';
    gameCtx.beginPath();
    gameCtx.moveTo(50, centerY);
    gameCtx.lineTo(width - 50, centerY);
    gameCtx.stroke();

    // Draw knot (current position)
    gameCtx.fillStyle = '#8b5a3c';
    gameCtx.beginPath();
    gameCtx.arc(ropeX, centerY, 15, 0, Math.PI * 2);
    gameCtx.fill();

    // Draw player indicators
    drawPlayer(gameCtx, 50, centerY, '#9146ff', 'left');
    drawPlayer(gameCtx, width - 50, centerY, '#ff6b6b', 'right');
}

function drawPlayer(ctx, x, y, color, side) {
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;

    // Draw stick figure
    // Head
    ctx.beginPath();
    ctx.arc(x, y - 30, 10, 0, Math.PI * 2);
    ctx.fill();

    // Body
    ctx.beginPath();
    ctx.moveTo(x, y - 20);
    ctx.lineTo(x, y + 10);
    ctx.stroke();

    // Arms (pulling position)
    ctx.beginPath();
    if (side === 'left') {
        ctx.moveTo(x, y - 10);
        ctx.lineTo(x + 15, y - 5);
        ctx.lineTo(x + 20, y);
    } else {
        ctx.moveTo(x, y - 10);
        ctx.lineTo(x - 15, y - 5);
        ctx.lineTo(x - 20, y);
    }
    ctx.stroke();

    // Legs
    ctx.beginPath();
    ctx.moveTo(x, y + 10);
    ctx.lineTo(x - 10, y + 30);
    ctx.moveTo(x, y + 10);
    ctx.lineTo(x + 10, y + 30);
    ctx.stroke();
}

function updateGame(state) {
    // Update rope position
    drawGame(state.rope_position);

    // Update stats
    document.getElementById('player1-pullers').textContent = state.player1_score;
    document.getElementById('player2-pullers').textContent = state.player2_score;
    document.getElementById('player1-engagement').textContent = (state.player1_engagement * 100).toFixed(1);
    document.getElementById('player2-engagement').textContent = (state.player2_engagement * 100).toFixed(1);

    // Update timer
    const minutes = Math.floor(state.time_remaining / 60);
    const seconds = state.time_remaining % 60;
    document.getElementById('game-timer').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

function showResult(winnerId, stats) {
    const isWinner = winnerId === currentUser.id;

    document.getElementById('result-title').textContent = isWinner ? 'Victory!' : 'Defeat!';
    document.getElementById('result-title').style.color = isWinner ? '#9146ff' : '#ff6b6b';
    document.getElementById('result-message').textContent = isWinner
        ? 'Your chat pulled through!'
        : 'Better luck next time!';

    showScreen('result-screen');

    // Reset room
    currentRoom = null;
}
