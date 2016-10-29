from .utils import checks

import discord
from discord.ext import commands

import youtube_dl
import math
import functools
import datetime
import time
import asyncio

if not discord.opus.is_loaded():
    discord.opus.load_opus('/usr/lib64/libopus.so.0')


class VoicePlayer:
    # This does not need to match up too closely to the StreamPlayer that is "technically" used here
    # This is more of a placeholder, just to keep the information that will be requested
    # Before the video is actually downloaded, which happens in our audio player task
    # For example, is_done() will not exist on this object, which could be called later
    # However, it should not ever be, as we overwrite this object with the StreamPlayer in our audio task
    def __init__(self, song, **kwargs):
        self.url = song
        self.views = kwargs.get('view_count')
        self.is_live = bool(kwargs.get('is_live'))
        self.likes = kwargs.get('likes')
        self.dislikes = kwargs.get('dislikes')
        self.duration = kwargs.get('duration')
        self.uploader = kwargs.get('uploader')
        if 'twitch' in song:
            self.title = kwargs.get('description')
            self.description = None
        else:
            self.title = kwargs.get('title')
            self.description = kwargs.get('description')

        date = kwargs.get('upload_date')
        if date:
            try:
                date = datetime.datetime.strptime(date, '%Y%M%d').date()
            except ValueError:
                date = None

        self.upload_date = date


class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player
        self.start_time = None

    @property
    def length(self):
        if self.player.duration:
            return self.player.duration
    
    @property
    def progress(self):
        if self.start_time:
            return round(time.time() - self.start_time)

    @property
    def remaining(self):
        length = self.length
        progress = self.progress
        if length and progress:
            return length - progress

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by {1.display_name}'
        duration = self.player.length
        if duration:
            fmt += ' [length: {0[0]}m {0[1]}s]'.format(divmod(round(duration, 0), 60))
        return fmt.format(self.player, self.requester)


class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        # This is the queue that holds all VoiceEntry's
        self.songs = asyncio.Queue(maxsize=10)
        self.required_skips = 0
        # a set of user_ids that voted
        self.skip_votes = set()
        # Our actual task that handles the queue system
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        self.opts = {
            'default_search': 'auto',
            'quiet': True
        }
        self.volume = 50

    def is_playing(self):
        # If our VoiceClient or current VoiceEntry do not exist, then we are not playing a song
        if self.voice is None or self.current is None:
            return False

        # If they do exist, check if the current player has finished
        player = self.current.player
        try:
            return not player.is_done()
        except AttributeError:
            return False

    @property
    def player(self):
        return self.current.player

    def skip(self):
        # Make sure we clear the votes, before stopping the player
        # When the player is stopped, our toggle_next method is called, so the next song can be played
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        # Set the Event so that the next song in the queue can be played
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            # At the start of our task, clear the Event, so we can wait till it is next set
            self.play_next_song.clear()
            # Clear the votes skip that were for the last song
            self.skip_votes.clear()
            # Set current to none while we are waiting for the next song in the queue
            # If we don't do this and we hit the end of the queue
            # our current song will remain the song that just finished
            self.current = None
            # Now wait for the next song in the queue
            self.current = await self.songs.get()
            # Tell the channel that requested the new song that we are now playing
            try:
                await self.bot.send_message(self.current.channel, 'Now playing ' + str(self.current))
            except discord.Forbidden:
                pass
            # Create the player object; this automatically creates the ffmpeg player
            self.current.player = await self.voice.create_ytdl_player(self.current.player.url, ytdl_options=self.opts,
                                                                      after=self.toggle_next)
            # Now we can start actually playing the song
            self.current.player.start()
            self.current.player.volume = self.volume / 100

            # Save the variable for when our time for this song has started
            self.current.start_time = time.time()

            # Wait till the Event has been set, before doing our task again
            await self.play_next_song.wait()


class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        self.opts = {
            'format': 'webm[abr>0]/bestaudio/best',
            'prefer_ffmpeg': True,
            'default_search': 'auto',
            'quiet': True
        }
        # We want to create our own YoutubeDL object to avoid downloading a video when first searching it
        # We will download the actual video, in our audio_player_task, for which we can just use create_ytdl_player
        self.ytdl = youtube_dl.YoutubeDL(self.opts)

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)

        # Internally handle creating a voice state if there isn't a current state
        # This can be used for example, in case something is skipped when not being connected
        # We create the voice state when checked
        # This only creates the state, we are still not playing anything, which can then be handled separately
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        # First join the channel and get the VoiceClient that we'll use to save per server
        try:
            voice = await self.bot.join_voice_channel(channel)
        except asyncio.TimeoutError:
            await self.bot.say(
                "Sorry, I couldn't connect! This can sometimes be caused by the server region you are in. "
                "You can either try again, or try to change the server's region and see if that fixes the issue")
            return
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        # If this is unloaded, cancel all players and disconnect from all channels
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    async def on_voice_state_update(self, before, after):
        state = self.get_voice_state(after.server)
        if state.voice is None:
            return
        voice_channel = state.voice.channel
        if voice_channel != before.voice.voice_channel and voice_channel != after.voice.voice_channel:
            return
        num_members = len(voice_channel.voice_members)
        state.required_skips = math.ceil((num_members + 1) / 3)

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def progress(self, ctx):
        """Provides the progress of the current song"""

        # Make sure we're playing first
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing anything.')
        else:
            progress = state.current.progress
            length = state.current.length
            # Another check, just to make sure; this may happen for a very brief amount of time
            # Between when the song was requested, and still downloading to play
            if not progress or not length:
                await self.bot.say('Not playing anything.')
                return

            # Otherwise just format this nicely
            progress = divmod(round(progress, 0), 60)
            length = divmod(round(length, 0), 60)
            fmt = "Current song progress: {0[0]}m {0[1]}s/{1[0]}m {1[1]}s"
            await self.bot.say(fmt)



    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def join(self, ctx, *, channel: discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        # Check if the channel given was an actual voice channel
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        # Check if we failed to join a channel, which means we are already in a channel.
        # move_channel needs to be used if we are already in a channel
        except discord.ClientException:
            state = self.get_voice_state(ctx.message.server)
            if state.voice is None:
                voice_channel = self.bot.voice_client_in(ctx.message.server)
                if voice_channel is not None:
                    await voice_channel.disconnect()
                await self.bot.say("Sorry but I failed to connect! Please try again")
            else:
                await state.voice.move_to(channel)
                await self.bot.say('Ready to play audio in ' + channel.name)
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        # This method will be invoked by other commands, so we should return True or False instead of just returning
        # First check if the author is even in a voice_channel
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        # Check if we're in a channel already, if we are then we just need to move channels
        # Otherwse, we need to create an actual voice state
        state = self.get_voice_state(ctx.message.server)
        # Discord's voice connecting is not very reliable, so we need to implement
        # a couple different workarounds here in case something goes wrong

        # First check if we have a voice connection saved
        if state.voice is not None:
            # Check if our saved voice connection doesn't actually exist
            if self.bot.voice_client_in(ctx.message.server) is None:
                await state.voice.disconnect()
                await self.bot.say("I had an issue connecting to the channel, please try again")
                return False
            # If it does exist, then we are in a voice channel already, and need to move to the new channel
            else:
                await state.voice.move_to(summoned_channel)
        # Otherwise, our connection is not detected by this cog
        else:
            # Check if there is actually a voice connection though
            voice_channel = self.bot.voice_client_in(ctx.message.server)
            if voice_channel is not None:
                await voice_channel.disconnect()
                await self.bot.say("I had an issue connecting to the channel, please try again")
                return False
            # In this case, nothing has gone wrong, and we aren't in a channel, so we can join it
            else:
                try:
                    state.voice = await self.bot.join_voice_channel(summoned_channel)
                # Weird timeout error usually caused by the region someone is in
                except (asyncio.TimeoutError, discord.ConnectionClosed, ConnectionResetError):
                    await self.bot.say(
                        "Sorry, I couldn't connect! This can sometimes be caused by the server region you are in. "
                        "You can either try again, or try to change the server's"
                        " region and see if that fixes the issue")
                    return False
        # Return true if nothing has failed, so that we can invoke this, and ensure we succeeded
        return True

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def play(self, ctx, *, song: str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """

        state = self.get_voice_state(ctx.message.server)

        # First check if we are connected to a voice channel at all, if not summon to the channel the author is in
        # Since summon checks if the author is in a channel, we don't need to handle that here, just return if it failed
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        # If the queue is full, we ain't adding anything to it
        if state.songs.full():
            await self.bot.say("The queue is currently full! You'll need to wait to add a new song")
            return

        author_channel = ctx.message.author.voice.voice_channel
        my_channel = ctx.message.server.me.voice.voice_channel

        # To try to avoid some abuse, ensure the requester is actually in our channel
        if my_channel != author_channel:
            await self.bot.say("You are not currently in the channel; please join before trying to request a song.")
            return

        # Create the player, and check if this was successful
        # Here all we want is to get the information of the player
        try:
            func = functools.partial(self.ytdl.extract_info, song, download=False)
            info = await self.bot.loop.run_in_executor(None, func)
            if "entries" in info:
                info = info['entries'][0]
            player = VoicePlayer(song, **info)
            # player = await state.voice.create_ytdl_player(song, ytdl_options=state.opts, after=state.toggle_next)
        except youtube_dl.DownloadError:
            fmt = "Sorry, either I had an issue downloading that video, or that's not a supported URL!"
            await self.bot.send_message(ctx.message.channel, fmt)
            return
        except IndexError:
            fmt = "Sorry, but there's no result with that search time! Try something else"
            await self.bot.send_message(ctx.message.channel, fmt)
            return
        except ValueError:
            fmt = "Brackets are my enemy; please remove them or else!\n" \
                  "(Youtube_dl errors when brackets are used, try running this again without the brackets)"
            await self.bot.send_message(ctx.message.channel, fmt)
            return

        # Now we can create a VoiceEntry and queue it
        entry = VoiceEntry(ctx.message, player)
        await state.songs.put(entry)
        try:
            await self.bot.say('Enqueued ' + str(entry))
        except discord.Forbidden:
            pass

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def volume(self, ctx, value: int = None):
        """Sets the volume of the currently playing song."""

        state = self.get_voice_state(ctx.message.server)
        if value is None:
            volume = state.volume
            await self.bot.say("Current volume is {}".format(volume))
            return
        if value > 200:
            await self.bot.say("Sorry but the max volume is 200")
            return
        state.volume = value
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Set the volume to {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            state.player.pause()

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            state.player.resume()

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        # Stop playing whatever song is playing.
        if state.is_playing():
            player = state.player
            player.stop()

        # This will stop cancel the audio event we're using to loop through the queue
        # Then erase the voice_state entirely, and disconnect from the channel
        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play"""
        # Note: There is no way to tell how long a song has been playing, or how long there is left on a song
        # That is why this is called an "ETA"
        state = self.get_voice_state(ctx.message.server)
        author = ctx.message.author

        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return
        queue = state.songs._queue
        if len(queue) == 0:
            await self.bot.say("Nothing currently in the queue")
            return

        # Start off by adding the length of the current song
        count = state.current.player.duration
        found = False
        # Loop through the songs in the queue, until the author is found as the requester
        # The found bool is used to see if we actually found the author, or we just looped through the whole queue
        for song in queue:
            if song.requester == author:
                found = True
                break
            count += song.player.duration

        # This is checking if nothing from the queue has been added to the total
        # If it has not, then we have not looped through the queue at all
        # Since the queue was already checked to have more than one song in it, this means the author is next
        if count == state.current.player.duration:
            await self.bot.say("You are next in the queue!")
            return
        if not found:
            await self.bot.say("You are not in the queue!")
            return
        await self.bot.say("ETA till your next play is: {0[0]}m {0[1]}s".format(divmod(round(count, 0), 60)))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        # Asyncio provides no non-private way to access the queue, so we have to use _queue
        queue = state.songs._queue
        if len(queue) == 0:
            fmt = "Nothing currently in the queue"
        else:
            fmt = "\n\n".join(str(x) for x in queue)
        await self.bot.say("Current songs in the queue:```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        await self.bot.say("There are a total of {} songs in the queue"
                           .format(str(self.get_voice_state(ctx.message.server).songs.qsize())))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        approximately 1/3 of the members in the voice channel
        are required to vote to skip for the song to be skipped.
        """

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        # Check if the person requesting a skip is the requester of the song, if so automatically skip
        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Requester requested skipping song...')
            state.skip()
        # Otherwise check if the voter has already voted
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)

            # Now check how many votes have been made, if 3 then go ahead and skip, otherwise add to the list of votes
            if total_votes >= state.required_skips:
                await self.bot.say('Skip vote passed, skipping song...')
                state.skip()
            else:
                await self.bot.say('Skip vote added, currently at [{}/{}]'.format(total_votes, state.required_skips))
        else:
            await self.bot.say('You have already voted to skip this song.')

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        state.skip()
        await self.bot.say('Song has just been skipped.')

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing anything.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Now playing {} [skips: {}/{}]'.format(state.current, skip_count, state.required_skips))


def setup(bot):
    bot.add_cog(Music(bot))
