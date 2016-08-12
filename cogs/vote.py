# XXX Make me!

import asyncio
import discord
from discord.ext import commands
from .utils import config
from .utils import checks

class Vote:
    """Voting made simple!"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def join(self, *, channel: discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        except discord.ClientException:
            await self.bot.say('Already in a voice channel...')
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
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
            await self.bot.say("The queue is currently full! You'll need to wait to add a new song")
            return
            
        author_channel = ctx.message.author.voice.voice_channel
        my_channel = ctx.message.server.me.voice.voice_channel
        
        if my_channel != author_channel:
            await self.bot.say("You are not currently in the channel; please join before trying to request a song.")
            return
        
        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=state.opts, after=state.toggle_next)
        except youtube_dl.DownloadError:
            await self.bot.send_message(ctx.message.channel,"Sorry, that's not a supported URL!")
            return
        player.volume = 0.6
        entry = VoiceEntry(ctx.message, player)
        await self.bot.say('Enqueued ' + str(entry))
        await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

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
            await self.bot.say('Not playing any music right now...')
            return
        if len(state.songs._queue) == 0:
            await self.bot.say("Nothing currently in the queue")
            return
        
        count = state.current.player.duration
        found = False
        for song in state.songs._queue:
            if song.requester == author:
                found = True
                break
            count += song.player.duration
        if count == state.current.player.duration:
            await self.bot.say("You are next in the queue!")
            return
        if not found:
            await self.bot.say("You are not in the queue!")
            return
        await self.bot.say("ETA till your next play is: {0[0]}m {0[1]}s".format(divmod(round(count, 0), 60)))
    
    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return
        if len(state.songs._queue) == 0:
            fmt = "Nothing currently in the queue"
        else:
            fmt = "\n\n".join(str(x) for x in state.songs._queue)
        await self.bot.say("Current songs in the queue:```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        await self.bot.say("There are a total of {} songs in the queue"
                           .format(str(self.get_voice_state(ctx.message.server).songs.qsize())))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        3 skip votes are needed for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/3]'.format(total_votes))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        state.skip()
        await self.bot.say('Song has just been skipped.')

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/3]'.format(state.current, skip_count))


def setup(bot):
    bot.add_cog(Music(bot))