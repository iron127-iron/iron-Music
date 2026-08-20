import discord
from core.config import bot, EMOJI
from core.helpers import anime_embed
from core.blacklist import blacklist, save_blacklist, user_blacklist, save_user_blacklist, BLACKLIST_ADMIN_ID

# =========================
# BLACKLIST / USERBLACKLIST
# =========================

@bot.command(name="blacklist", aliases=["bl", "blacklis", "黑名單"])
async def blacklist_cmd(ctx, action=None, *, value=None):
    if ctx.author.id != BLACKLIST_ADMIN_ID:
        return await ctx.send(f"{EMOJI['error']} 你沒有權限管理黑名單")

    if action is None:
        action = "list"

    if action == "list":
        if not blacklist:
            return await ctx.send(f"{EMOJI['clear']} 黑名單是空的")
        embed = anime_embed(
            title=f"{EMOJI['error']} 黑名單（{len(blacklist)} 筆）"
        )
        for i, item in enumerate(blacklist, 1):
            embed.add_field(name=f"`{i}.`", value=f"`{item}`", inline=False)
        await ctx.send(embed=embed)
        return

    if action == "clear":
        blacklist.clear()
        save_blacklist(blacklist)
        return await ctx.send(f"{EMOJI['success']} 已清空黑名單")

    if action == "remove":
        if not value:
            return await ctx.send(f"{EMOJI['error']} 用法：`=blacklist remove <關鍵字/網址>`")
        target = value.lower()
        removed = [x for x in blacklist if target not in x.lower()]
        count = len(blacklist) - len(removed)
        if count == 0:
            return await ctx.send(f"{EMOJI['warn']} 黑名單中沒有符合的項目")
        blacklist[:] = removed
        save_blacklist(blacklist)
        return await ctx.send(f"{EMOJI['success']} 已移除 **{count}** 筆：`{value}`")

    item = action
    if value:
        item = f"{action} {value}"
    item = item.strip()
    if not item:
        return await ctx.send(f"{EMOJI['error']} 用法：`=blacklist <關鍵字/網址>`")

    if item.lower() in [x.lower() for x in blacklist]:
        return await ctx.send(f"{EMOJI['warn']} `{item}` 已在黑名單中")

    blacklist.append(item)
    save_blacklist(blacklist)

    embed = anime_embed(
        title=f"{EMOJI['success']} 已加入黑名單",
        description=f"`{item}`\n\n包含此關鍵字、網址或影片 ID 的歌曲將無法播放"
    )
    await ctx.send(embed=embed)

@bot.command(name="userblacklist", aliases=["ubl", "ublacklist"])
async def userblacklist_cmd(ctx, action=None, *, value=None):
    if ctx.author.id != BLACKLIST_ADMIN_ID:
        return await ctx.send(f"{EMOJI['error']} 你沒有權限管理使用者黑名單")

    if action is None:
        action = "list"

    if action == "list":
        if not user_blacklist:
            return await ctx.send(f"{EMOJI['clear']} 使用者黑名單是空的")
        embed = anime_embed(
            title=f"{EMOJI['error']} 使用者黑名單（{len(user_blacklist)} 筆）"
        )
        for i, uid in enumerate(user_blacklist, 1):
            embed.add_field(name=f"`{i}.` <@{uid}>", value=f"ID：`{uid}`", inline=False)
        await ctx.send(embed=embed)
        return

    if action == "clear":
        user_blacklist.clear()
        save_user_blacklist(user_blacklist)
        return await ctx.send(f"{EMOJI['success']} 已清空使用者黑名單")

    if action == "remove":
        if not value:
            return await ctx.send(f"{EMOJI['error']} 用法：`=userblacklist remove <使用者ID>`")
        try:
            target = int(value)
        except ValueError:
            return await ctx.send(f"{EMOJI['error']} 請提供有效的使用者 ID")
        if target not in user_blacklist:
            return await ctx.send(f"{EMOJI['warn']} 該使用者不在黑名單中")
        user_blacklist.remove(target)
        save_user_blacklist(user_blacklist)
        return await ctx.send(f"{EMOJI['success']} 已將 <@{target}> 移出黑名單")

    try:
        target = int(action)
    except ValueError:
        return await ctx.send(f"{EMOJI['error']} 用法：`=userblacklist <使用者ID>`")

    if target == BLACKLIST_ADMIN_ID:
        return await ctx.send(f"{EMOJI['error']} 不能封鎖管理員自己")
    if target in user_blacklist:
        return await ctx.send(f"{EMOJI['warn']} <@{target}> 已在黑名單中")

    user_blacklist.append(target)
    save_user_blacklist(user_blacklist)

    embed = anime_embed(
        title=f"{EMOJI['success']} 已封鎖使用者",
        description=f"<@{target}>（`{target}`）\n\n此使用者的指令將被忽略"
    )
    await ctx.send(embed=embed)