from .voice_utilities import *
from discord import FFmpegPCMAudio, PCMVolumeTransformer

import discord
from discord.ext import commands

from . import utils

import math
import asyncio
import inspect
import time
import re
import logging
import traceback

log = logging.getLogger()

if not discord.opus.is_loaded():
    discord.opus.load_opus('/usr/lib64/libopus.so.0')


class VoiceState:
    def __init__(self, guild, bot):
        self.guild = guild
        self.songs = Playlist(bot)
        self.current = None
        self.required_skips = 0
        self.skip_votes = set()
        self.audio_player = bot.loop.create_task(self.audio_player_task())
        self._volume = 50

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, v):
        self._volume = v
        if self.voice and self.voice.source:
            self.voice.source.volume = v

    @property
    def voice(self):
        return self.guild.voice_client

    @property
    def playing(self):
        if self.voice is None:
            return False
        else:
            return self.voice.is_playing() or self.voice.is_paused()

    def skip(self):
        self.skip_votes.clear()
        if self.playing:
            self.voice.stop()

    def after(self):
        self.current = None

    async def audio_player_task(self):
        fmt = ""
        while True:
            if self.playing:
                await asyncio.sleep(1)
                continue
            song = self.songs.peek()
            if song is None:
                await asyncio.sleep(1)
                continue

            try:
                self.current = await self.songs.get_next_entry()
                embed = self.current.to_embed()
                embed.title = "Now playing!"
                await song.channel.send(embed=embed)
            except ExtractionError as e:
                error = str(e).partition(" ")[2]
                await song.channel.send("Failed to download {}!\nError: {}".format(song.title, error))
                continue
            except Exception as e:
                await song.channel.send("Failed to download {}!".format(song.title))
                log.error(traceback.format_exc())
                continue


            source = FFmpegPCMAudio(
                self.current.filename,
                before_options='-nostdin',
                options='-vn -b:a 128k'
            )
            source = PCMVolumeTransformer(source, volume=self.volume)
            self.voice.play(source, after=self.after)
            self.current.start_time = time.time()


class Music:
    """Voice related commands.
    Works in multiple servers at once.
    """

    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}
        down = Downloader(download_folder='audio_tmp')
        self.downloader = down
        self.bot.downloader = down

    def __unload(self):
        # If this is unloaded, cancel all players and disconnect from all channels
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    async def queue_embed_task(self, state, channel, author):
        index = 0
        message = None
        fmt = None
        possible_reactions = ['\u27A1', '\u2B05', '\u2b06', '\u2b07', '\u274c']

        # Our check to ensure the only one who reacts is the bot
        def check(react, u):
            if message is None:
                return False
            elif react.message.id != message.id:
                return False
            elif react.emoji not in possible_reactions:
                return False
            else:
                return u.id == author.id

        while True:
            # Get the current queue (It might change while we're doing this)
            # So do this in the while loop
            queue = state.songs.entries
            count = len(queue)
            # This means the last song was removed
            if count == 0:
                await channel.send("Nothing currently in the queue")
                break
            # Get the current entry
            entry = queue[index]
            # Get the entry's embed
            embed = entry.to_embed()
            # Set the embed's title to indicate the amount of things in the queue
            count = len(queue)
            embed.title = "Current Queue [{}/{}]".format(index + 1, count)
            # Now we need to send the embed, so check if the message is already set
            # If not, then we need to send a new one (i.e. this is the first time called)
            if message:
                await message.edit(content=fmt, embed=embed)
                # There's only one reaction we want to make sure we remove in the circumstances
                # If the member doesn't have kick_members permissions, and isn't the requester
                # Then they can't remove the song, otherwise they can
                if not author.guild_permissions.kick_members and author.id != entry.requester.id:
                    try:
                        await message.remove_reaction('\u274c', channel.server.me)
                    except:
                        pass
                elif not author.guild_permissions.kick_members and author.id == entry.requester.id:
                    try:
                        await message.add_reaction('\u274c')
                    except:
                        pass
            else:
                message = await channel.send(embed=embed)
                await message.add_reaction('\N{LEFTWARDS BLACK ARROW}')
                await message.add_reaction('\N{BLACK RIGHTWARDS ARROW}')
                # The moderation tools that can be used
                if author.guild_permissions.kick_members:
                    await message.add_reaction('\N{DOWNWARDS BLACK ARROW}')
                    await message.add_reaction('\N{UPWARDS BLACK ARROW}')
                    await message.add_reaction('\N{CROSS MARK}')
                elif author == entry.requester:
                    await message.add_reaction('\N{CROSS MARK}')
            # Reset the fmt message
            fmt = "\u200B"
            # Now we wait for the next reaction
            try:
                reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=180)
            except asyncio.TimeoutError:
                break
            # Now we can prepare for the next embed to be sent
            # If right is clicked
            if '\u27A1' in reaction.emoji:
                index += 1
                if index >= count:
                    index = 0
            # If left is clicked
            elif '\u2B05' in reaction.emoji:
                index -= 1
                if index < 0:
                    index = count - 1
            # If up is clicked
            elif '\u2b06' in reaction.emoji:
                # A second check just to make sure, as well as ensuring index is higher than 0
                if author.guild_permissions.kick_members and index > 0:
                    if entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Remove the current entry
                        del queue[index]
                        # Add it one position higher
                        queue.insert(index - 1, entry)
                        # Lets move the index to look at the new place of the entry
                        index -= 1
            # If down is clicked
            elif '\u2b07' in reaction.emoji:
                # A second check just to make sure, as well as ensuring index is lower than last
                if author.guild_permissions.kick_members and index < (count - 1):
                    if entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Remove the current entry
                        del queue[index]
                        # Add it one position lower
                        queue.insert(index + 1, entry)
                        # Lets move the index to look at the new place of the entry
                        index += 1
            # If x is clicked
            elif '\u274c' in reaction.emoji:
                # A second check just to make sure
                if author.guild_permissions.kick_members or author == entry.requester:
                    if entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Simply remove the entry in place
                        del queue[index]
                        # This is the only check we need to make, to ensure index is now not more than last
                        new_count = count - 1
                        if index >= new_count:
                            index = new_count - 1
            try:
                await message.remove_reaction(reaction.emoji, user)
            except discord.Forbidden:
                pass
        await message.delete()

    async def on_voice_state_update(self, member, before, after):
        if after is None or after.channel is None:
            return
        state = self.voice_states.get(after.channel.guild.id)
        if state is None or state.voice is None or state.voice.channel is None:
            return
        voice_channel = state.voice.channel
        num_members = len(voice_channel.members)
        state.required_skips = math.ceil((num_members + 1) / 3)

    async def add_entry(self, song, ctx):
        state = self.voice_states[ctx.message.guild.id]
        entry, _ = await state.songs.add_entry(song, ctx)
        return entry

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def progress(self, ctx):
        """Provides the progress of the current song"""

        # Make sure we're playing first
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing anything.')
        else:
            progress = state.current.progress
            length = state.current.length
            # Another check, just to make sure; this may happen for a very brief amount of time
            # Between when the song was requested, and still downloading to play
            if not progress or not length:
                await ctx.send('Not playing anything.')
                return

            # Otherwise just format this nicely
            progress = divmod(round(progress, 0), 60)
            length = divmod(round(length, 0), 60)
            fmt = "Current song progress: {0[0]}m {0[1]}s/{1[0]}m {1[1]}s".format(progress, length)
            await ctx.send(fmt)

    @commands.command(aliases=['summon'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """Joins a voice channel. Provide the name of a voice channel after the command, and
        I will attempt to join this channel. Otherwise, I will join the channel you are in.

        EXAMPLE: !join Music
        RESULT: I have joined the music channel"""
        if channel is None:
            if ctx.message.author.voice is None or ctx.message.author.voice.channel is None:
                await ctx.send("You need to either be in a voice channel, or provide the name of a voice channel!")
                return False
            channel = ctx.message.author.voice.channel

        perms = channel.permissions_for(ctx.message.guild.me)

        if not perms.connect or not perms.speak or not perms.use_voice_activation:
            await ctx.send("I do not have correct permissions in {}! Please turn on `connect`, `speak`, and `use "
                           "voice activation`".format(channel.name))
            return False

        log.info("Connecting to {} in {}".format(channel.id, ctx.message.guild.id))
        state = self.voice_states.get(ctx.message.guild.id)
        try:
            if state and state.voice and state.voice.channel:
                await state.voice.move_to(channel)
                await ctx.send("Joined {} and ready to play".format(channel.name))
                return True
            else:
                self.voice_states[ctx.message.guild.id] = VoiceState(ctx.message.guild, self.bot)
                await channel.connect()
                await ctx.send("Joined {} and ready to play".format(channel.name))
                return True
        except asyncio.TimeoutError:
            await ctx.send("Sorry, but I couldn't connect right now! Please try again later")
            return False

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def play(self, ctx, *, song: str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        if ctx.message.guild.id not in self.voice_states:
            if not await ctx.invoke(self.join):
                return

        song = re.sub('[<>\[\]]', '', song)

        try:
            entry = await self.add_entry(song, ctx)
        except asyncio.TimeoutError:
            await ctx.send("You took too long!")
        except LiveStreamError as e:
            await ctx.send(str(e))
        else:
            if entry is None:
                await ctx.send("Sorry but I couldn't download/find {}".format(song))
            else:
                embed = entry.to_embed()
                embed.title = "Enqueued song!"
                await ctx.send(embed=embed)

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def volume(self, ctx, value: int = None):
        """Sets the volume of the currently playing song."""

        state = self.voice_states.get(ctx.message.guild.id)
        if value:
            value = value / 100
        if state is None or state.voice is None:
            await ctx.send("I need to be in a channel before my volume can be set")
        elif value is None:
            await ctx.send('Current volume is {:.0%}'.format(state.voice.source.volume))
        elif value > 1.0:
            await ctx.send("Sorry but the max volume is 100%")
        else:
            state.volume = value
            await ctx.send('Set the volume to {:.0%}'.format(state.voice.source.volume))

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.voice_states.get(ctx.message.guild.id)
        if state and state.voice and state.voice.is_connected():
            state.voice.pause()

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.voice_states.get(ctx.message.guild.id)
        if state and state.voice and state.voice.is_connected():
            state.voice.resume()

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        state = self.voice_states.get(ctx.message.guild.id)

        # Stop playing whatever song is playing.
        if state and state.voice:
            state.voice.stop()

            state.songs.clear()

            # This will cancel the audio event we're using to loop through the queue
            # Then erase the voice_state entirely, and disconnect from the channel
            state.audio_player.cancel()
            await state.voice.disconnect()
            del self.voice_states[ctx.message.guild.id]

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play"""
        # Note: There is no way to tell how long a song has been playing, or how long there is left on a song
        # That is why this is called an "ETA"
        state = self.voice_states.get(ctx.message.guild.id)
        author = ctx.message.author

        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return

        queue = state.songs.entries
        if len(queue) == 0:
            await ctx.send("Nothing currently in the queue")
            return

        # Start off by adding the remaining length of the current song
        count = state.current.remaining
        found = False
        # Loop through the songs in the queue, until the author is found as the requester
        # The found bool is used to see if we actually found the author, or we just looped through the whole queue
        for song in queue:
            if song.requester == author:
                found = True
                break
            count += song.duration

        if not found:
            await ctx.send("You are not in the queue!")
            return
        await ctx.send("ETA till your next play is: {0[0]}m {0[1]}s".format(divmod(round(count, 0), 60)))

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None:
            await ctx.send("Nothing currently in the queue")
            return
        # Asyncio provides no non-private way to access the queue, so we have to use _queue
        _queue = state.songs.entries
        if len(_queue) == 0:
            await ctx.send("Nothing currently in the queue")
        else:
            self.bot.loop.create_task(self.queue_embed_task(state, ctx.message.channel, ctx.message.author))

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        await ctx.send("There are a total of {} songs in the queue"
                       .format(len(self.voice_states.get(ctx.message.guild.id).songs.entries)))

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        approximately 1/3 of the members in the voice channel
        are required to vote to skip for the song to be skipped.
        """

        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return

        # Check if the person requesting a skip is the requester of the song, if so automatically skip
        voter = ctx.message.author
        if voter == state.current.requester:
            await ctx.send('Requester requested skipping song...')
            state.skip()
        # Otherwise check if the voter has already voted
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)

            # Now check how many votes have been made, if 3 then go ahead and skip, otherwise add to the list of votes
            if total_votes >= state.required_skips:
                await ctx.send('Skip vote passed, skipping song...')
                state.skip()
            else:
                await ctx.send('Skip vote added, currently at [{}/{}]'.format(total_votes, state.required_skips))
        else:
            await ctx.send('You have already voted to skip this song.')

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return

        state.skip()
        await ctx.send('Song has just been skipped.')

    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing anything.')
        else:
            # Create the embed object we'll use
            embed = discord.Embed()
            # Fill in the simple things
            embed.add_field(name='Title', value=state.current.title, inline=False)
            embed.add_field(name='Requester', value=state.current.requester.display_name, inline=False)
            # Get the amount of current skips, and display how many have been skipped/how many required
            skip_count = len(state.skip_votes)
            embed.add_field(name='Skip Count', value='{}/{}'.format(skip_count, state.required_skips), inline=False)
            # Get the current progress and display this
            progress = state.current.progress
            length = state.current.length
            progress = divmod(round(progress, 0), 60)
            length = divmod(round(length, 0), 60)
            fmt = "{0[0]}m {0[1]}s/{1[0]}m {1[1]}s".format(progress, length)
            embed.add_field(name='Progress', value=fmt, inline=False)
            # And send the embed
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Music(bot))
