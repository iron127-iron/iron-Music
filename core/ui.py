import discord
from core.config import EMOJI, THEME
from core.settings import _t_lang
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.player import Player

class MusicUI(discord.ui.View):

    def __init__(self, player: "Player"):
        super().__init__(timeout=None)
        self.player = player

    @discord.ui.button(label="▶ 繼續", style=discord.ButtonStyle.green, emoji="▶️")
    async def play(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message(f"{EMOJI['resume']} 已繼續播放", ephemeral=True)
        else:
            await interaction.response.send_message("⏸️ 目前已在播放中", ephemeral=True)

    @discord.ui.button(label="⏸ 暫停", style=discord.ButtonStyle.gray, emoji="⏸️")
    async def pause(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message(f"{EMOJI['pause']} 已暫停播放", ephemeral=True)
        else:
            await interaction.response.send_message("▶️ 目前未在播放", ephemeral=True)

    @discord.ui.button(label="⏭ 跳過", style=discord.ButtonStyle.red, emoji="⏭️")
    async def skip(self, interaction, button):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            self.player._manual_skip = True
            vc.stop()
            await interaction.response.send_message(f"{EMOJI['skip']} 已跳過", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 沒有正在播放的歌曲", ephemeral=True)

    @discord.ui.button(label="🔁 循環", style=discord.ButtonStyle.blurple, emoji="🔁")
    async def loop(self, interaction, button):
        self.player.loop = not self.player.loop
        t = lambda key, **kw: _t_lang(self.player.lang, key, **kw)
        await interaction.response.send_message(
            f"{t('loop_on') if self.player.loop else t('loop_off')}",
            ephemeral=True
        )
        if self.player.message:
            try:
                await self.player.message.edit(embed=self.player.now_playing_embed(), view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(label="⏩ 倍速", style=discord.ButtonStyle.blurple, emoji="⏩")
    async def speed(self, interaction, button):
        order = [1.0, 1.5, 2.0, 0.5]
        current = self.player.speed
        idx = order.index(current) if current in order else 0
        rate = order[(idx + 1) % len(order)]
        ok = await self.player.set_speed(rate)
        t = lambda key, **kw: _t_lang(self.player.lang, key, **kw)
        await interaction.response.send_message(
            f"⏩ 倍速：**{rate}x**" + ("" if ok else "（無法重啟，已設為下次播放生效）"),
            ephemeral=True
        )
        if self.player.message:
            try:
                await self.player.message.edit(embed=self.player.now_playing_embed(), view=self)
            except (discord.NotFound, discord.HTTPException):
                pass

    @discord.ui.button(label="🔊 音量", style=discord.ButtonStyle.green, emoji="🔊")
    async def volume(self, interaction, button):

        class VolumeView(discord.ui.View):

            def __init__(self, player, timeout=20):
                super().__init__(timeout=timeout)
                self.player = player

            async def on_timeout(self):
                try:
                    await interaction.message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass

            def _volume_embed(self):
                embed = discord.Embed(
                    title="🔊 音量控制",
                    description=_t_lang(self.player.lang, 'volume_now', v=int(self.player.volume*100)),
                    color=THEME
                )
                embed.set_footer(text="🎀 點擊按鈕調整音量 💖")
                return embed

            async def _adjust_volume(self, interaction, delta):
                async with self.player.volume_lock:
                    self.player.volume = max(0.0, min(1.5, self.player.volume + delta))
                    vc = interaction.guild.voice_client
                    if vc and vc.source:
                        vc.source.volume = self.player.volume
                await interaction.response.edit_message(
                    content=f"🔊 音量：{int(self.player.volume*100)}%",
                    embed=self._volume_embed(),
                    view=self
                )

            @discord.ui.button(label="－10", style=discord.ButtonStyle.red, row=0)
            async def vol_down_10(self, interaction, button):
                await self._adjust_volume(interaction, -0.10)

            @discord.ui.button(label="－5", style=discord.ButtonStyle.red, row=0)
            async def vol_down_5(self, interaction, button):
                await self._adjust_volume(interaction, -0.05)

            @discord.ui.button(label="－1", style=discord.ButtonStyle.gray, row=0)
            async def vol_down_1(self, interaction, button):
                await self._adjust_volume(interaction, -0.01)

            @discord.ui.button(label="＋1", style=discord.ButtonStyle.green, row=1)
            async def vol_up_1(self, interaction, button):
                await self._adjust_volume(interaction, 0.01)

            @discord.ui.button(label="＋5", style=discord.ButtonStyle.green, row=1)
            async def vol_up_5(self, interaction, button):
                await self._adjust_volume(interaction, 0.05)

            @discord.ui.button(label="＋10", style=discord.ButtonStyle.green, row=1)
            async def vol_up_10(self, interaction, button):
                await self._adjust_volume(interaction, 0.10)

        embed = discord.Embed(
            title="🔊 音量控制",
            description=_t_lang(self.player.lang, 'volume_now', v=int(self.player.volume*100)),
            color=THEME
        )
        embed.set_footer(text="🎀 點擊按鈕調整音量 💖")
        await interaction.response.send_message(embed=embed, view=VolumeView(self.player), ephemeral=True)

class SearchUI(discord.ui.View):

    def __init__(self, entries, ctx, player, timeout=60):
        super().__init__(timeout=timeout)
        self.entries = entries
        self.ctx = ctx
        self.player = player

    @discord.ui.button(label="1️⃣", style=discord.ButtonStyle.blurple, row=0)
    async def one(self, interaction, button):
        await self.pick(interaction, 0)

    @discord.ui.button(label="2️⃣", style=discord.ButtonStyle.blurple, row=0)
    async def two(self, interaction, button):
        await self.pick(interaction, 1)

    @discord.ui.button(label="3️⃣", style=discord.ButtonStyle.blurple, row=0)
    async def three(self, interaction, button):
        await self.pick(interaction, 2)

    @discord.ui.button(label="4️⃣", style=discord.ButtonStyle.blurple, row=1)
    async def four(self, interaction, button):
        await self.pick(interaction, 3)

    @discord.ui.button(label="5️⃣", style=discord.ButtonStyle.blurple, row=1)
    async def five(self, interaction, button):
        await self.pick(interaction, 4)

    async def pick(self, interaction, idx):
        if idx >= len(self.entries):
            return await interaction.response.send_message("❌ 無效選擇", ephemeral=True)

        from core.helpers import extract_song
        from core.blacklist import is_blacklisted

        song = extract_song(self.entries[idx])

        blocked = is_blacklisted(song)
        if blocked:
            return await interaction.response.send_message(
                f"🚫 此歌曲已被封鎖（`{blocked}`）",
                ephemeral=True
            )

        self.player.queue.append(song)

        if self.ctx.voice_client and self.ctx.voice_client.is_playing():
            from core.config import EMOJI
            from core.helpers import anime_embed
            embed = anime_embed(
                title=f"{EMOJI['success']} 已加入隊列",
                description=f"**[{song['title']}]({song.get('url')})**",
            )
            await interaction.message.edit(embed=embed, view=None)
            await interaction.response.send_message("✅ 已加入隊列", ephemeral=True)
        else:
            await interaction.message.edit(content="✅ 即將播放", view=None)
            await interaction.response.send_message("✅ 已加入隊列", ephemeral=True)