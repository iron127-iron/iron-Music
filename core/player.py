import asyncio
import time
import discord
from collections import deque
from core.settings import guild_lang, record_play, _t_lang
from core.stream import spawn_stream, write_diag, stream_error, FFMPEG, RETRY_CLIENTS
from core.config import FFMPEG_PATH
from core.helpers import progress_bar

class Player:

    def __init__(self, ctx):
        self.bot = ctx.bot if hasattr(ctx, 'bot') else ctx.client
        self.channel = ctx.channel
        self.guild_id = ctx.guild.id if hasattr(ctx, 'guild') and ctx.guild else ctx.guild_id
        self.lang = guild_lang(self.guild_id)
        self.owner_id = ctx.author.id if hasattr(ctx, 'author') else ctx.user.id
        self.voice = None

        self.queue = deque()
        self.current = None
        self.history = deque(maxlen=30)

        self.loop = False
        self.volume = 0.5
        self.speed = 1.0
        self._base_media_pos = 0.0
        self._suppress_next = False
        self._manual_skip = False

        self.message = None

        self.start = 0
        self.duration = 0

        self.next_event = asyncio.Event()
        self.volume_lock = asyncio.Lock()

        self._proc = None
        self._stopped = False
        self._last_failed = False
        self._last_error = ""
        self._last_log_path = ""

        self.bot.loop.create_task(self.loop_player())

    def _kill_proc(self):
        if self._proc:
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None

    def _stream_ffmpeg(self, url, ss=0, clients=None, is_speed_change=False):
        self._kill_proc()
        self._proc = spawn_stream(url, clients=clients)
        self._last_log_path = getattr(self._proc, "_log_path", "")
        before = "-nostdin"
        dur = self.duration or 0
        fade_in = "0.15" if is_speed_change else "1.2"
        fade_out = "0.15" if is_speed_change else "1.2"
        filters = [f"afade=t=in:st=0:d={fade_in}"]
        if dur > float(fade_out) + 0.3:
            filters.append(f"afade=t=out:st={dur - float(fade_out)}:d={fade_out}")
        filters.append(f"atempo={self.speed}")
        af = ",".join(filters)
        options = f"-vn -ss {ss} -af \"{af}\"" if ss else f"-vn -af \"{af}\""
        return discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                self._proc.stdout,
                pipe=True,
                executable=FFMPEG_PATH,
                before_options=before,
                options=options,
            ),
            volume=self.volume
        )

    def _stream_failed(self):
        if not self._proc or self._proc.poll() is None:
            return False
        return self._proc.returncode != 0

    def _start_source(self, url, ss=0, clients=None, is_speed_change=False):
        if not self.voice or not self.voice.is_connected():
            return None

        source = self._stream_ffmpeg(url, ss, clients, is_speed_change)
        if self._stream_failed():
            self._last_error = stream_error(self._proc)
            self._last_failed = True
            write_diag(self._proc, f"immediate fail: {self._last_error!r}")
            self._kill_proc()
            return None

        self.start = time.time()
        self._base_media_pos = ss
        proc = self._proc

        def after(_):
            rc = proc.poll() if proc else None
            write_diag(proc, f"after fired rc={rc} failed={self._last_failed}")
            if self._suppress_next:
                self._suppress_next = False
                if proc:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                return
            if self._manual_skip:
                self._manual_skip = False
                self._last_error = ""
                self._last_failed = False
                self._kill_proc()
                self.bot.loop.call_soon_threadsafe(self.next_event.set)
                return
            self._last_error = stream_error(proc) if proc and proc.poll() not in (None, 0) else ""
            self._last_failed = bool(self._last_error)
            write_diag(proc, f"last_error={self._last_error!r}")
            self._kill_proc()
            self.bot.loop.call_soon_threadsafe(self.next_event.set)

        try:
            self.voice.play(source, after=after)
        except Exception as e:
            print(f"[play error] {e}")
            self._last_error = str(e)
            self._last_failed = True
            self._kill_proc()
            return None
        return source

    def _manual_restart(self, url, ss, is_speed_change=False):
        if not self.voice or not self.voice.is_connected():
            return False
        self._suppress_next = True
        try:
            self.voice.stop()
        except Exception:
            pass
        return self._start_source(url, ss, is_speed_change=is_speed_change) is not None

    async def set_speed(self, rate):
        if rate not in (0.5, 1.0, 1.5, 2.0):
            return False
        song = self.current
        if not song:
            return False
        url = song.get("url") or song.get("webpage_url")
        media_pos = self._base_media_pos + (time.time() - self.start) * self.speed
        if self.duration and media_pos > self.duration:
            media_pos = self.duration
        self.speed = rate
        if not self.voice or not self.voice.is_connected() or not self.voice.is_playing():
            return True
        return self._manual_restart(url, media_pos, is_speed_change=True)

    def progress(self):
        if not self.current:
            return "無播放內容"
        if self.duration == 0:
            return "🔴 直播中"
        now = self._base_media_pos + (time.time() - self.start) * self.speed
        return progress_bar(now, self.duration)

    def now_playing_embed(self):
        song = self.current
        t = lambda key, **kw: _t_lang(self.lang, key, **kw)
        embed = discord.Embed(
            title=f"{t('now_playing')}",
            description=f"**[{song['title']}]({song.get('url')})**",
            color=discord.Color.from_rgb(255, 105, 180)
        )
        embed.add_field(name=f"⏱ {t('progress')}", value=self.progress(), inline=False)
        status = []
        status.append(t('loop_on') if self.loop else t('loop_off'))
        status.append(t('volume', v=int(self.volume*100)))
        status.append(t('speed', s=self.speed))
        status.append(t('queue_count', n=len(self.queue)))
        embed.add_field(name=f"📊 {t('status')}", value=" | ".join(status), inline=False)
        embed.set_footer(text="🎀 Iron Music Bot 💖")
        return embed

    async def send_panel(self):
        from core.ui import MusicUI
        for attempt in range(3):
            try:
                self.message = await self.channel.send(
                    embed=self.now_playing_embed(),
                    view=MusicUI(self)
                )
                return True
            except discord.HTTPException:
                if attempt < 2:
                    await asyncio.sleep(1 + attempt * 2)
                else:
                    self.message = None
                    return False
        return False

    async def loop_player(self):
        while not self._stopped:
            if not self.voice or not self.voice.is_connected():
                await asyncio.sleep(1)
                continue
            if not self.queue:
                await asyncio.sleep(1)
                continue

            self.current = self.queue.popleft()
            self.history.append(dict(self.current))
            record_play(self.current, self.current.get("duration", 0))
            self.duration = self.current.get("duration", 0)

            ok = await self._play_track_with_retry(self.current)

            if self._stopped:
                break

            if not ok:
                if self._last_failed:
                    await self._notify_stream_failed()
                    self._last_failed = False
                continue

            if self.loop:
                self.queue.append(self.current)

            if not self.loop and not self.queue:
                await self._notify_queue_finished()

    async def _play_track_with_retry(self, song):
        url = song.get("url") or song.get("webpage_url")
        for attempt in range(len(RETRY_CLIENTS) or 3):
            if self._stopped:
                return True
            try:
                source = self._start_source(url, 0, clients=RETRY_CLIENTS[attempt])
            except Exception as e:
                print(f"[stream error] {song.get('title')}: {e}")
                self._last_error = str(e)
                self._last_failed = True
                await asyncio.sleep(1.5)
                continue
            if source is None:
                await asyncio.sleep(1.5)
                continue

            if self.message:
                try:
                    await self.message.delete()
                except (discord.NotFound, discord.HTTPException):
                    pass
                self.message = None

            await self.send_panel()
            self.next_event.clear()
            await self.next_event.wait()

            if self._stopped:
                return True
            if not self._last_failed:
                return True

            write_diag(self._proc, f"retry same song, attempt={attempt+1}")
            await asyncio.sleep(1.5)
        return False

    async def _notify_queue_finished(self):
        try:
            user = self.bot.get_user(self.owner_id)
            if not user:
                user = await self.bot.fetch_user(self.owner_id)
            if user:
                from core.config import EMOJI
                await user.send(f"{EMOJI['music']} 隊列已全部播放完畢！")
        except Exception as e:
            print(f"[dm error] {e}")

    async def _notify_stream_failed(self):
        song = self.current
        err = self._last_error
        if not err and self._last_log_path:
            try:
                with open(self._last_log_path, "rb") as f:
                    for line in reversed(f.read().decode("utf-8", "ignore").splitlines()):
                        if line.strip():
                            err = line.strip()[:200]
                            break
            except Exception:
                pass
        try:
            from core.config import EMOJI
            embed = discord.Embed(
                title=f"{EMOJI['error']} 無法播放此歌曲",
                description=f"**[{song.get('title', '未知標題')}]({song.get('url') or '#'})**\n\nYouTube 拒絕提供串流（可能是地區/驗證限制），已跳過",
                color=discord.Color.from_rgb(255, 105, 180)
            )
            embed.add_field(name="原因", value=f"`{(err or '串流失敗')[:180]}`", inline=False)
            embed.set_footer(text="🎀 Iron Music Bot 💖")
            await self.channel.send(embed=embed)
        except Exception as e:
            print(f"[notify error] {e}")

# Import MusicUI after to avoid circular import
from core.ui import MusicUI