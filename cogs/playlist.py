import asyncio
import discord
from discord.ext import commands
from .utils import checks
from .utils.config import getPhrase
import youtube_dl

if not discord.opus.is_loaded():
    discord.opus.load_opus("/usr/lib64/libopus.so.0") # Assuming 


class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player
        self.votes_needed = 3

    def __str__(self):
        fmt = getPhrase("PLAYER:GET_TRACK_NAME")
        duration = self.player.duration
        if duration:
            d = divmod(round(duration, 0), 60)
            fmt += " " + getPhrase("PLAYER:GET_TRACK_LENGTH").format(d[0], d[1])
        return fmt.format(self.player.title, self.player.uploader, self.requester.display_name)


class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue(maxsize=10)
        self.skip_votes = set()  # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        self.opts = {
            "default_search": "auto",
            "quiet": True,
        }

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.skip_votes.clear()
            self.current = None
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, getPhrase("PLAYER:NOW_PLAYING").format(str(self.current)))

            self.current.player = await self.voice.create_ytdl_player(self.current.player.url, ytdl_options=self.opts,
                                                                      after=self.toggle_next)
            self.current.player.start()
            await self.play_next_song.wait()


class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def join(self, *, channel: discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.InvalidArgument:
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_VOICE_CHANNEL"))
        except discord.ClientException:
            await self.bot.say(getPhrase("PLAYER:ERROR_ALREADY_JOINED"))
        except Exception as e:
            fmt = getPhrase("ERROR_DEBUG_COMMAND_FAIL") + " ```py\n{}: {}\n```"
            await self.bot.say(fmt.format(type(e).__name__, e))
        else:
            await self.bot.say(getPhrase("PLAYER:READY").format(channel.name))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say(getPhrase("PLAYER:ERROR_USER_NOT_IN_CHANNEL"))
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)
        return True

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def play(self, ctx, *, song: str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        if state.songs.full():
            await self.bot.say(getPhrase("PLAYER:ERROR_QUEUE_FULL"))
            return
            
        author_channel = ctx.message.author.voice.voice_channel
        my_channel = ctx.message.server.me.voice.voice_channel
        
        if my_channel != author_channel:
            await self.bot.say(getPhrase("PLAYER:ERROR_USER_NOT_IN_CHANNEL_PLAY"))
            return
        
        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=state.opts, after=state.toggle_next)
        except youtube_dl.DownloadError:
            await self.bot.send_message(ctx.message.channel, getPhrase("PLAYER:ERROR_UNSUPPORTED_URL"))
            return
        player.volume = 0.6
        entry = VoiceEntry(ctx.message, player)
        await self.bot.say(getPhrase("PLAYER:SONG_ENQUEUED").format(str(entry)))
        await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say(getPhrase("PLAYER:VOLUME_CHANGED").format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass
    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play"""
        state = self.get_voice_state(ctx.message.server)
        author = ctx.message.author
        
        if not state.is_playing():
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_PLAYING"))
            return
        if len(state.songs._queue) == 0:
            await self.bot.say(getPhrase("PLAYER:ERROR_QUEUE_EMPTY"))
            return
        
        count = state.current.player.duration
        found = False
        for song in state.songs._queue:
            if song.requester == author:
                found = True
                break
            count += song.player.duration
        if count == state.current.player.duration:
            await self.bot.say(getPhrase("PLAYER:NEXT_IN_QUEUE"))
            return
        if not found:
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_IN_QUEUE"))
            return
        eta = divmod(round(count, 0), 60)
        await self.bot.say(getPhrase("PLAYER:ETA").format(eta[0], eta[1]))
    
    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_PLAYING"))
            return
        if len(state.songs._queue) == 0:
            fmt = getPhrase("PLAYER:ERROR_QUEUE_EMPTY")
        else:
            fmt = "\n\n".join(str(x) for x in state.songs._queue)
        await self.bot.say(getPhrase("PLAYER:LIST_QUEUE")+"```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        await self.bot.say(getPhrase("PLAYER:COUNT_QUEUE").format(str(self.get_voice_state(ctx.message.server).songs.qsize())))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip."""

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_PLAYING"))
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say(getPhrase("PLAYER:SKIP_REQUESTER"))
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= self.votes_needed:
                await self.bot.say(getPhrase("PLAYER:SKIP_VOTES"))
                state.skip()
            else:
                await self.bot.say(getPhrase("PLAYER:SKIP_VOTE_ADDED").format(total_votes, self.votes_needed))
        else:
            await self.bot.say(getPhrase("PLAYER:ERROR_ALREADY_SKIP_VOTED"))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_PLAYING"))
            return

        state.skip()
        await self.bot.say(getPhrase("PLAYER:SKIP_MOD"))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say(getPhrase("PLAYER:ERROR_NOT_PLAYING"))
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say(getPhrase("PLAYER:NOW_PLAYING").format(state.current) + getPhrase("PLAYER:GET_SKIP_COUNT").format(skip_count, self.votes_needed))


def setup(bot):
    bot.add_cog(Music(bot))
