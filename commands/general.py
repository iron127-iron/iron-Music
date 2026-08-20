import discord
from core.config import bot, EMOJI, PREFIX
from core.helpers import anime_embed

# =========================
# HELP / PING / ABOUT / INFO
# =========================

@bot.command()
async def help(ctx, category=None):
    embed = anime_embed(
        title="🎀 Iron Music Bot 指令",
        description="用 `=help <分類>` 查看詳細指令\n用 `=help 音樂` 查看音樂指令"
    )

    basic = """
`=help` → 指令列表
`=ping` → 延遲
`=about` → 機器人資訊
`=serverinfo` → 伺服器資訊
`=userinfo` → 使用者資訊
"""

    music = f"""
`=play <名稱/URL>` → 播放音樂
`=play <播放列表URL>` → 播放列表
`=search <名稱>` → 搜尋並選擇
`=skip` → 跳過
`=stop` → 停止並離開
`=pause` → 暫停
`=resume` → 繼續
`=queue [頁碼]` → 隊列
`=remove <編號>` → 移除隊列歌曲
`=move <來源> <目標>` → 移動隊列歌曲
`=history [編號]` → 播放歷史（可再播）
`=nowplaying` → 目前歌曲
`=volume [0-150]` → 音量
`=shuffle` → 洗牌
`=clear` → 清空隊列
`=seek <秒>` → 跳轉時間
`=speed <0.5|1|1.5|2>` → 播放倍速
`=download [名稱/URL]` → 下載目前歌曲為 mp3
`=lyrics` → 歌詞
`=subtitles [語言]` → 導出字幕，沒有就自動生成 (.srt)
`=loop` → 循環（按鈕）
`=stats` → 播放統計
`=language <zh-TW|zh-CN|en>` → 語系設定
`=blacklist <關鍵字/網址>` → 歌曲黑名單（管理員）
`=userblacklist <使用者ID>` → 使用者黑名單（管理員）
"""

    if not category:
        embed.add_field(name="🌸 基本指令", value=basic, inline=False)
        embed.add_field(name="🎶 音樂指令", value=music, inline=False)
    elif category == "基本":
        embed.description = basic
    elif category == "音樂":
        embed.description = music
    else:
        embed.description = f"{EMOJI['error']} 找不到分類"

    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    embed = anime_embed(
        title="🏓 Pong!",
        description=f"延遲：**{round(bot.latency * 1000)}ms**"
    )
    embed.add_field(name="💖 狀態", value="在線", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def about(ctx):
    embed = anime_embed(
        title="🎀 Iron Music Bot",
        description="一個可愛的音樂機器人 💖"
    )
    embed.add_field(name="🌐 功能", value="🎵 播放音樂\n🔊 音量控制\n⏩ 倍速調整\n📜 隊列管理\n🔀 洗牌\n📝 歌詞\n🕘 播放歷史\n⬇️ 下載\n📊 統計\n🌐 多語系", inline=False)
    embed.add_field(name="👑 作者", value="Iron Studio", inline=True)
    embed.add_field(name="🐍 技術", value="discord.py + yt-dlp", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = anime_embed(
        title=f"🌸 {guild.name}",
        description=f"伺服器資訊"
    )
    embed.add_field(name="👥 成員", value=guild.member_count, inline=True)
    embed.add_field(name="📁 頻道", value=len(guild.channels), inline=True)
    embed.add_field(name="👑 擁有者", value=guild.owner.mention, inline=True)
    embed.add_field(name="📅 建立時間", value=guild.created_at.strftime("%Y/%m/%d"), inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = anime_embed(
        title=f"🌸 {member.display_name}",
        description=f"使用者資訊"
    )
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="📅 加入時間", value=member.joined_at.strftime("%Y/%m/%d"), inline=True)
    embed.add_field(name="🤖 機器人", value="是" if member.bot else "否", inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)