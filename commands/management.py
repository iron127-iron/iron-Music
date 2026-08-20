import discord
from discord.ext import commands
import sys
import importlib
import os
import json
from core.config import bot, EMOJI
from core.helpers import anime_embed

OWNER_ID = 1299949671090749462
ADMIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "admins.json")

def load_admins():
    if os.path.exists(ADMIN_FILE):
        with open(ADMIN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_admins(admins):
    with open(ADMIN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(admins), f)

ADMINS = load_admins()

def is_owner(ctx):
    return ctx.author.id == OWNER_ID

def is_admin(ctx):
    return ctx.author.id == OWNER_ID or ctx.author.id in ADMINS

MODULES = {
    "music": "音樂播放指令 (play, search, queue等)",
    "search": "搜尋功能",
    "queue": "隊列管理 (queue, remove, move, clear, shuffle)",
    "control": "播放控制 (nowplaying, volume, seek, speed)",
    "lyrics": "歌詞搜尋與顯示",
    "subtitles": "字幕導出與 Whisper 自動生成",
    "download": "音樂下載 (MP3)",
    "stats": "播放統計",
    "language": "語系設定",
    "playback": "播放面板按鈕交互",
    "general": "基本指令 (help, ping, about, serverinfo, userinfo)",
    "blacklist": "黑名單管理 (歌曲/使用者)",
    "management": "機器人管理指令 (reload <模組/all>, list, restart [bot|pal], load, unload, addadmin, unadmin, adminlist)",
}

@bot.group(name="mc", invoke_without_command=True)
@commands.check(is_admin)
async def mc_group(ctx):
    embed = anime_embed(
        title=f"{EMOJI['sparkle']} IronBot 管理面板",
        description="子指令：\n`=mc list` → 列出所有模組\n`=mc reload <模組/all>` → 重載模組（all 為全部）\n`=mc restart [bot|pal]` → 重啟機器人或 Palworld 伺服器\n`=mc load <模組>` → 載入模組\n`=mc unload <模組>` → 卸載模組\n`=mc addadmin <用戶>` → 新增管理員\n`=mc unadmin <用戶>` → 移除管理員\n`=mc adminlist` → 查看管理員列表"
    )
    await ctx.send(embed=embed)

@mc_group.command(name="list")
@commands.check(is_admin)
async def mc_list(ctx):
    embed = anime_embed(
        title=f"{EMOJI['queue']} 模組列表",
        description=f"共 {len(MODULES)} 個模組"
    )
    for name, desc in MODULES.items():
        embed.add_field(name=f"`{name}`", value=desc, inline=False)
    await ctx.send(embed=embed)

@mc_group.command(name="reload")
@commands.check(is_admin)
async def mc_reload(ctx, module: str = None):
    if not module:
        return await ctx.send(f"{EMOJI['error']} 用法：`=mc reload <模組名>` 或 `=mc reload all`")
    
    if module.lower() == "all":
        msg = await ctx.send(f"{EMOJI['star']} 正在重載所有模組...")
        success = []
        failed = []
        
        for mod_name in MODULES:
            if mod_name == "management":
                continue
            try:
                to_remove = []
                for cmd_name, cmd in list(bot.all_commands.items()):
                    if cmd.module and cmd.module.startswith(f"commands.{mod_name}"):
                        to_remove.append(cmd_name)
                for cmd_name in to_remove:
                    bot.remove_command(cmd_name)
                
                mod = sys.modules.get(f"commands.{mod_name}")
                if mod:
                    importlib.reload(mod)
                
                success.append(mod_name)
            except Exception as e:
                failed.append(f"{mod_name}: {e}")
        
        desc = f"{EMOJI['success']} 成功：{len(success)} 個\n"
        if success:
            desc += ", ".join(f"`{m}`" for m in success) + "\n"
        if failed:
            desc += f"\n{EMOJI['error']} 失敗：{len(failed)} 個\n"
            desc += "\n".join(f"`{m}`" for m in failed)
        
        embed = anime_embed(
            title=f"{EMOJI['star']} 全模組重載完成",
            description=desc
        )
        await msg.edit(content=None, embed=embed)
        return
    
    if module not in MODULES:
        return await ctx.send(f"{EMOJI['error']} 找不到模組：`{module}`\n用 `=mc list` 查看可用模組")
    
    try:
        to_remove = []
        for cmd_name, cmd in list(bot.all_commands.items()):
            if cmd.module and cmd.module.startswith(f"commands.{module}"):
                to_remove.append(cmd_name)
        for cmd_name in to_remove:
            bot.remove_command(cmd_name)
        
        mod = sys.modules.get(f"commands.{module}")
        if mod:
            importlib.reload(mod)
        
        await ctx.send(f"{EMOJI['success']} 已重載模組：`{module}`")
    except Exception as e:
        await ctx.send(f"{EMOJI['error']} 重載失敗：{e}")

@mc_group.command(name="restart")
@commands.check(is_owner)
async def mc_restart(ctx, target: str = "bot"):
    """重啟機器人或 Palworld 伺服器
    用法：=mc restart [bot|pal]
    """
    target = target.lower()
    
    if target == "bot":
        embed = anime_embed(
            title=f"{EMOJI['warn']} 重啟機器人...",
            description="Discord 機器人即將重啟，請稍候...\n\n**重啟完成後無法在此頻道收到訊息**（進程已結束）\n請查看：\n• 控制台輸出 `[OK] 機器人已上線`\n• 狀態更新為 `聽音樂`\n• 進程管理器 日誌"
        )
        await ctx.send(embed=embed)
        await bot.close()
        os._exit(0)
    
    elif target == "pal":
        embed = anime_embed(
            title=f"{EMOJI['warn']} 重啟 Palworld 伺服器...",
            description="正在發送重啟指令到 MCSManager..."
        )
        await ctx.send(embed=embed)
        
        # Try to restart via MCSManager API
        try:
            import subprocess
            result = subprocess.run(
                ["powershell", "-Command", "Restart-Service", "MCSManager"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                await ctx.send(f"{EMOJI['success']} Palworld 伺服器重啟指令已發送")
            else:
                await ctx.send(f"{EMOJI['error']} 重啟失敗：{result.stderr or result.stdout}")
        except Exception as e:
            await ctx.send(f"{EMOJI['error']} 重啟異常：{e}")
    
    else:
        await ctx.send(f"{EMOJI['error']} 未知目標：`{target}`\n可用：`bot`、`pal`")

@mc_group.command(name="unload")
@commands.check(is_admin)
async def mc_unload(ctx, module: str = None):
    if not module:
        return await ctx.send(f"{EMOJI['error']} 用法：`=mc unload <模組名>`")
    
    if module not in MODULES:
        return await ctx.send(f"{EMOJI['error']} 找不到模組：`{module}`\n用 `=mc list` 查看可用模組")
    
    if module == "management":
        return await ctx.send(f"{EMOJI['error']} 無法卸載管理模組自身")
    
    try:
        to_remove = []
        for cmd_name, cmd in list(bot.all_commands.items()):
            if cmd.module and cmd.module.startswith(f"commands.{module}"):
                to_remove.append(cmd_name)
        for cmd_name in to_remove:
            bot.remove_command(cmd_name)
        
        mod_name = f"commands.{module}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        
        await ctx.send(f"{EMOJI['success']} 已卸載模組：`{module}`")
    except Exception as e:
        await ctx.send(f"{EMOJI['error']} 卸載失敗：{e}")

@mc_group.command(name="load")
@commands.check(is_admin)
async def mc_load(ctx, module: str = None):
    if not module:
        return await ctx.send(f"{EMOJI['error']} 用法：`=mc load <模組名>`")
    
    if module not in MODULES:
        return await ctx.send(f"{EMOJI['error']} 找不到模組：`{module}`\n用 `=mc list` 查看可用模組")
    
    try:
        mod_name = f"commands.{module}"
        if mod_name in sys.modules:
            del sys.modules[mod_name]
        
        importlib.import_module(mod_name)
        
        await ctx.send(f"{EMOJI['success']} 已載入模組：`{module}`")
    except Exception as e:
        await ctx.send(f"{EMOJI['error']} 載入失敗：{e}")

@mc_group.command(name="addadmin")
@commands.check(is_owner)
async def mc_addadmin(ctx, user: discord.User = None):
    if not user:
        return await ctx.send(f"{EMOJI['error']} 用法：`=mc addadmin <@用戶/用戶ID>`")
    
    if user.id == OWNER_ID:
        return await ctx.send(f"{EMOJI['warn']} 擁有者已是最高權限")
    
    if user.id in ADMINS:
        return await ctx.send(f"{EMOJI['warn']} 該用戶已是管理員")
    
    ADMINS.add(user.id)
    save_admins(ADMINS)
    await ctx.send(f"{EMOJI['success']} 已新增管理員：{user.mention} (`{user.id}`)")

@mc_group.command(name="unadmin")
@commands.check(is_owner)
async def mc_unadmin(ctx, user: discord.User = None):
    if not user:
        return await ctx.send(f"{EMOJI['error']} 用法：`=mc unadmin <@用戶/用戶ID>`")
    
    if user.id == OWNER_ID:
        return await ctx.send(f"{EMOJI['error']} 無法移除擁有者權限")
    
    if user.id not in ADMINS:
        return await ctx.send(f"{EMOJI['warn']} 該用戶不是管理員")
    
    ADMINS.remove(user.id)
    save_admins(ADMINS)
    await ctx.send(f"{EMOJI['success']} 已移除管理員：{user.mention} (`{user.id}`)")

@mc_group.command(name="adminlist")
@commands.check(is_admin)
async def mc_adminlist(ctx):
    embed = anime_embed(
        title=f"{EMOJI['star']} 管理員列表",
        description=f"擁有者：<@{OWNER_ID}>\n管理員：{len(ADMINS)} 位"
    )
    if ADMINS:
        for admin_id in ADMINS:
            embed.add_field(name=f"<@{admin_id}>", value=f"`{admin_id}`", inline=True)
    else:
        embed.description += "\n(無)"
    await ctx.send(embed=embed)

@mc_group.error
async def mc_group_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send(f"{EMOJI['error']} 僅限管理員使用")
    else:
        raise error