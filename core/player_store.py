from collections import deque
from core.player import Player
import discord

players = {}

def get_player(ctx):
    guild_id = ctx.guild.id if hasattr(ctx, 'guild') and ctx.guild else ctx.guild_id
    if guild_id not in players:
        players[guild_id] = Player(ctx)
    return players[guild_id]