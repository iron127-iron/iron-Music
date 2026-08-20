import asyncio
import json
import os
import secrets
from aiohttp import web
from aiohttp.web import Request, Response
import socketio
from aiohttp_session import setup, get_session, new_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
import aiohttp
from aiohttp import web_middleware

from core.config import bot
from core.player_store import players

# =========================
# CONFIG - 修改這些為你的實際值
# =========================
# Discord OAuth2
DISCORD_CLIENT_ID = '1539155008811962441'
DISCORD_CLIENT_SECRET = '12yTnEDpRsVsAcwEfxzJQwliZSF4HsUr'
# OAuth 回調指向「前端域名」 (GitHub Pages)
DISCORD_REDIRECT_URI = 'https://YOUR_GITHUB_USERNAME.github.io/iron-music-bot-panel/callback'
DISCORD_API_BASE = 'https://discord.com/api'

# 前端域名 (GitHub Pages) - 用於 CORS
FRONTEND_ORIGIN = 'https://YOUR_GITHUB_USERNAME.github.io'

# 後端綁定
WEB_PORT = int(os.getenv('WEB_PANEL_PORT', '12700'))
WEB_HOST = os.getenv('WEB_PANEL_HOST', '0.0.0.0')

# Session
SESSION_SECRET = secrets.token_bytes(32)

# Discord API
DISCORD_API_BASE = 'https://discord.com/api'

# =========================
# SOCKET.IO & WEB APP
# =========================
sio = socketio.AsyncServer(
    async_mode='aiohttp', 
    cors_allowed_origins=[FRONTEND_ORIGIN, 'https://tpe-cht1.taiwanfrp.me:12700']
)
web_app = web.Application()

# Session setup
setup(web_app, EncryptedCookieStorage(SESSION_SECRET))

# CORS Middleware
@web_middleware
async def cors_middleware(request, handler):
    if request.method == 'OPTIONS':
        response = web.Response()
    else:
        response = await handler(request)
    
    response.headers['Access-Control-Allow-Origin'] = FRONTEND_ORIGIN
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

web_app.middlewares.append(cors_middleware)

# Debug middleware
@web.middleware
async def debug_middleware(request, handler):
    print(f'[WEB] {request.method} {request.path}')
    try:
        response = await handler(request)
        print(f'[WEB] Response: {response.status}')
        return response
    except Exception as e:
        print(f'[WEB] Error: {e}')
        raise

web_app.middlewares.append(debug_middleware)
web_app.middlewares.append(cors_middleware)

sio.attach(web_app, socketio_path='/socket.io')

# Session setup
from aiohttp_session import setup, get_session, new_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
SESSION_SECRET = secrets.token_bytes(32)
setup(web_app, EncryptedCookieStorage(SESSION_SECRET))

# =========================
# STATE MANAGEMENT
# =========================
connected_clients = set()
sid_to_user = {}

def get_user_voice_state(user_id, guild_id):
    guild = bot.get_guild(guild_id)
    if not guild:
        return None
    member = guild.get_member(user_id)
    if not member or not member.voice or not member.voice.channel:
        return None
    return member.voice.channel.id

def user_can_control(user_id, guild_id, bot_voice_channel_id):
    user_vc_id = get_user_voice_state(user_id, guild_id)
    return user_vc_id == bot_voice_channel_id

def get_bot_state(user=None):
    guilds = []
    for guild in bot.guilds:
        guild_id = guild.id
        player = players.get(guild_id)
        bot_vc_id = player.voice.channel.id if player and player.voice and player.voice.channel else None
        
        can_control = False
        if user:
            user_vc_id = get_user_voice_state(user['id'], guild_id)
            can_control = user_vc_id == bot_vc_id if bot_vc_id else False
        
        guilds.append({
            'id': str(guild_id),
            'name': guild.name,
            'icon': str(guild.icon.url) if guild.icon else None,
            'bot_voice_channel': bot_vc_id,
            'can_control': can_control,
            'current': {
                'title': player.current.get('title') if player and player.current else None,
                'url': player.current.get('url') if player and player.current else None,
                'duration': player.current.get('duration') if player and player.current else 0,
            } if player and player.current else None,
            'queue': [
                {'title': s.get('title'), 'url': s.get('url'), 'duration': s.get('duration')}
                for s in list(player.queue)[:20]
            ] if player else [],
            'volume': int(player.volume * 100) if player else 50,
            'speed': player.speed if player else 1.0,
            'loop': player.loop if player else False,
            'playing': player.voice and player.voice.is_playing() if player and player.voice else False,
            'paused': player.voice and player.voice.is_paused() if player and player.voice else False,
            'progress': player.progress() if player and player.current else '無播放內容',
        })
    return {
        'bot_user': str(bot.user) if bot.user else '離線',
        'user': user,
        'guilds': guilds,
    }

async def broadcast_state():
    for sid in connected_clients.copy():
        try:
            await sio.emit('state', get_bot_state(), to=sid)
        except:
            connected_clients.discard(sid)

async def periodic_broadcast():
    while True:
        await asyncio.sleep(2)
        if connected_clients:
            await broadcast_state()

# =========================
# SOCKET.IO EVENTS
# =========================
@sio.event
async def connect(sid, environ):
    print(f'[WEB] Client connected: {sid}')
    connected_clients.add(sid)
    session = environ.get('aiohttp_session')
    user = session.get('user') if session else None
    if user:
        sid_to_user[sid] = user['id']
    await sio.emit('state', get_bot_state(user), to=sid)

@sio.event
async def disconnect(sid):
    print(f'[WEB] Client disconnected: {sid}')
    connected_clients.discard(sid)
    sid_to_user.pop(sid, None)

@sio.event
async def control(sid, data):
    action = data.get('action')
    guild_id = data.get('guild_id')
    if not guild_id:
        return {'error': 'guild_id required'}
    
    user_id = sid_to_user.get(sid)
    if not user_id:
        return {'error': 'not authenticated', 'need_login': True}
    
    guild_id_int = int(guild_id)
    player = players.get(guild_id_int)
    if not player:
        return {'error': 'no player'}
    
    bot_vc_id = player.voice.channel.id if player.voice and player.voice.channel else None
    if bot_vc_id and not user_can_control(user_id, guild_id_int, bot_vc_id):
        return {'error': 'you must be in the same voice channel as the bot to control it', 'need_voice': True}
    
    try:
        if action == 'play':
            await player.set_pause(False)
        elif action == 'pause':
            await player.set_pause(True)
        elif action == 'skip':
            player._manual_skip = True
            if player.voice:
                player.voice.stop()
        elif action == 'stop':
            player._stopped = True
            player._manual_skip = True
            player._kill_proc()
            player.next_event.set()
            if player.voice:
                await player.voice.disconnect()
        elif action == 'volume':
            vol = max(0, min(150, int(data.get('value', 50))))
            async with player.volume_lock:
                player.volume = vol / 100
                if player.voice and player.voice.source:
                    player.voice.source.volume = player.volume
        elif action == 'seek':
            seconds = max(0, int(data.get('value', 0)))
            if player.current:
                url = player.current.get('url') or player.current.get('webpage_url')
                player._manual_restart(url, seconds)
        elif action == 'speed':
            rate = float(data.get('value', 1.0))
            await player.set_speed(rate)
        elif action == 'loop':
            player.loop = not player.loop
        elif action == 'shuffle':
            import random
            songs = list(player.queue)
            random.shuffle(songs)
            player.queue = __import__('collections').deque(songs)
        elif action == 'clear':
            player.queue.clear()
        elif action == 'command':
            cmd_text = data.get('value', '').strip()
            if not cmd_text:
                return {'error': 'empty command'}
            try:
                guild = bot.get_guild(guild_id_int)
                if not guild:
                    return {'error': 'guild not found'}
                
                channel = None
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break
                if not channel:
                    return {'error': 'no sendable channel'}
                
                parts = cmd_text.split()
                cmd_name = parts[0].lower()
                args = parts[1:]
                
                cmd = bot.get_command(cmd_name)
                if not cmd:
                    return {'error': f'unknown command: {cmd_name}'}
                
                from unittest.mock import MagicMock
                fake_ctx = MagicMock()
                fake_ctx.guild = guild
                fake_ctx.channel = channel
                fake_ctx.author = guild.me
                fake_ctx.bot = bot
                fake_ctx.prefix = '='
                fake_ctx.invoked_with = cmd_name
                fake_ctx.args = args
                
                await cmd.invoke(fake_ctx)
                
                return {'success': True, 'output': f'執行指令: ={cmd_text}'}
            except Exception as e:
                return {'error': f'command error: {e}'}
        else:
            return {'error': f'unknown action: {action}'}
        
        await broadcast_state()
        return {'success': True}
    except Exception as e:
        return {'error': str(e)}

# =========================
# HTTP ROUTES (API Only)
# =========================
from aiohttp_session import get_session, new_session

async def login(request):
    if not DISCORD_CLIENT_ID:
        return web.Response(text='Discord OAuth2 not configured', status=500)
    
    state = secrets.token_urlsafe(32)
    session = await new_session(request)
    session['oauth2_state'] = state
    
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds voice',
        'state': state,
        'prompt': 'consent',
    }
    url = f'{DISCORD_API_BASE}/oauth2/authorize?' + '&'.join(f'{k}={v}' for k, v in params.items())
    return web.HTTPFound(url)

async def callback(request):
    code = request.query.get('code')
    state = request.query.get('state')
    error = request.query.get('error')
    
    if error:
        return web.Response(text=f'Discord OAuth error: {error}', status=400)
    
    session = await get_session(request)
    if session.get('oauth2_state') != state:
        return web.Response(text='Invalid state', status=400)
    
    if not code:
        return web.Response(text='No code provided', status=400)
    
    async with aiohttp.ClientSession() as http:
        data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        async with http.post(f'{DISCORD_API_BASE}/oauth2/token', data=data, headers=headers) as resp:
            if resp.status != 200:
                return web.Response(text='Failed to get token', status=500)
            token_data = await resp.json()
        
        access_token = token_data['access_token']
        
        async with http.get(f'{DISCORD_API_BASE}/users/@me', headers={'Authorization': f'Bearer {access_token}'}) as resp:
            if resp.status != 200:
                return web.Response(text='Failed to get user info', status=500)
            user_data = await resp.json()
        
        session = await new_session(request)
        session['user'] = {
            'id': int(user_data['id']),
            'username': user_data['username'],
            'discriminator': user_data['discriminator'],
            'avatar': user_data['avatar'],
            'access_token': access_token,
        }
    
    # Redirect back to frontend
    return web.HTTPFound('https://YOUR_GITHUB_USERNAME.github.io/iron-music-bot-panel/')

async def logout(request):
    session = await get_session(request)
    session.invalidate()
    return web.HTTPFound('https://YOUR_GITHUB_USERNAME.github.io/iron-music-bot-panel/')

async def me(request):
    session = await get_session(request)
    user = session.get('user')
    if not user:
        return web.json_response({'user': None})
    return web.json_response({'user': user})

async def check_voice(request):
    session = await get_session(request)
    user = session.get('user')
    if not user:
        return web.json_response({'error': 'not authenticated'}, status=401)
    
    guild_id = request.query.get('guild_id')
    if not guild_id:
        return web.json_response({'error': 'guild_id required'}, status=400)
    
    guild_id_int = int(guild_id)
    player = players.get(guild_id_int)
    bot_vc_id = player.voice.channel.id if player and player.voice and player.voice.channel else None
    
    user_vc_id = get_user_voice_state(user['id'], guild_id_int)
    can_control = user_vc_id == bot_vc_id if bot_vc_id else False
    
    return web.json_response({
        'can_control': can_control,
        'bot_voice_channel': bot_vc_id,
        'user_voice_channel': user_vc_id,
    })

async def health(request):
    return web.json_response({'status': 'ok', 'clients': len(connected_clients)})

# =========================
# ROUTES
# =========================
web_app.router.add_get('/login', login)
web_app.router.add_get('/callback', callback)
web_app.router.add_get('/logout', logout)
web_app.router.add_get('/me', me)
web_app.router.add_get('/check_voice', check_voice)
web_app.router.add_get('/health', health)

# =========================
# STARTUP
# =========================
async def start_web_panel():
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    print(f'[WEB] API Server started: http://{WEB_HOST}:{WEB_PORT}')
    print(f'[WEB] CORS Origin: {FRONTEND_ORIGIN}')
    print(f'[WEB] Discord Redirect: {DISCORD_REDIRECT_URI}')
    asyncio.create_task(periodic_broadcast())
    return runner

# Socket.io events (placed after function definitions)
sid_to_user = {}

@sio.event
async def connect(sid, environ):
    print(f'[WEB] Client connected: {sid}')
    connected_clients.add(sid)
    session = environ.get('aiohttp_session')
    user = session.get('user') if session else None
    if user:
        sid_to_user[sid] = user['id']
    await sio.emit('state', get_bot_state(user), to=sid)

@sio.event
async def disconnect(sid):
    print(f'[WEB] Client disconnected: {sid}')
    connected_clients.discard(sid)
    sid_to_user.pop(sid, None)

# Place control event handler here (moved from earlier)
@sio.event
async def control(sid, data):
    action = data.get('action')
    guild_id = data.get('guild_id')
    if not guild_id:
        return {'error': 'guild_id required'}
    
    user_id = sid_to_user.get(sid)
    if not user_id:
        return {'error': 'not authenticated', 'need_login': True}
    
    guild_id_int = int(guild_id)
    player = players.get(guild_id_int)
    if not player:
        return {'error': 'no player'}
    
    bot_vc_id = player.voice.channel.id if player.voice and player.voice.channel else None
    if bot_vc_id and not user_can_control(user_id, guild_id_int, bot_vc_id):
        return {'error': 'you must be in the same voice channel as the bot to control it', 'need_voice': True}
    
    try:
        if action == 'play':
            await player.set_pause(False)
        elif action == 'pause':
            await player.set_pause(True)
        elif action == 'skip':
            player._manual_skip = True
            if player.voice:
                player.voice.stop()
        elif action == 'stop':
            player._stopped = True
            player._manual_skip = True
            player._kill_proc()
            player.next_event.set()
            if player.voice:
                await player.voice.disconnect()
        elif action == 'volume':
            vol = max(0, min(150, int(data.get('value', 50))))
            async with player.volume_lock:
                player.volume = vol / 100
                if player.voice and player.voice.source:
                    player.voice.source.volume = player.volume
        elif action == 'seek':
            seconds = max(0, int(data.get('value', 0)))
            if player.current:
                url = player.current.get('url') or player.current.get('webpage_url')
                player._manual_restart(url, seconds)
        elif action == 'speed':
            rate = float(data.get('value', 1.0))
            await player.set_speed(rate)
        elif action == 'loop':
            player.loop = not player.loop
        elif action == 'shuffle':
            import random
            songs = list(player.queue)
            random.shuffle(songs)
            player.queue = __import__('collections').deque(songs)
        elif action == 'clear':
            player.queue.clear()
        elif action == 'command':
            cmd_text = data.get('value', '').strip()
            if not cmd_text:
                return {'error': 'empty command'}
            try:
                guild = bot.get_guild(guild_id_int)
                if not guild:
                    return {'error': 'guild not found'}
                
                channel = None
                for ch in guild.text_channels:
                    if ch.permissions_for(guild.me).send_messages:
                        channel = ch
                        break
                if not channel:
                    return {'error': 'no sendable channel'}
                
                parts = cmd_text.split()
                cmd_name = parts[0].lower()
                args = parts[1:]
                
                cmd = bot.get_command(cmd_name)
                if not cmd:
                    return {'error': f'unknown command: {cmd_name}'}
                
                from unittest.mock import MagicMock
                fake_ctx = MagicMock()
                fake_ctx.guild = guild
                fake_ctx.channel = channel
                fake_ctx.author = guild.me
                fake_ctx.bot = bot
                fake_ctx.prefix = '='
                fake_ctx.invoked_with = cmd_name
                fake_ctx.args = args
                
                await cmd.invoke(fake_ctx)
                
                return {'success': True, 'output': f'執行指令: ={cmd_text}'}
            except Exception as e:
                return {'error': f'command error: {e}'}
        else:
            return {'error': f'unknown action: {action}'}
        
        await broadcast_state()
        return {'success': True}
    except Exception as e:
        return {'error': str(e)}

async def start_web_panel():
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    print(f'[WEB] API Server started: http://{WEB_HOST}:{WEB_PORT}')
    print(f'[WEB] CORS Origin: {FRONTEND_ORIGIN}')
    print(f'[WEB] Discord Redirect: {DISCORD_REDIRECT_URI}')
    asyncio.create_task(periodic_broadcast())
    return runner