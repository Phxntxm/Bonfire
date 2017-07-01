from .voice_utilities import *
from discord import FFmpegPCMAudio, PCMVolumeTransformer

import discord
from discord.ext import commands

from . import utils

import math
import asyncio
import time
import re
import logging
import random
from collections import deque

log = logging.getLogger()

if not discord.opus.is_loaded():
    discord.opus.load_opus('/usr/lib64/libopus.so.0')


class VoiceState:
    def __init__(self, guild, bot, user_queue=False):
        self.guild = guild
        self.songs = Playlist(bot)
        self.djs = deque()
        self.dj = None
        self.current = None
        self.required_skips = 0
        self.skip_votes = set()
        self.user_queue = user_queue
        self.loop = bot.loop
        self._volume = .5

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

    def switch_queue_type(self):
        self.songs.clear()
        self.djs.clear()
        self.dj = None
        self.user_queue = not self.user_queue
        self.skip()

    def get_dj(self, member):
        for x in self.djs:
            if x.member.id == member.id:
                return x

    def skip(self):
        self.skip_votes.clear()
        if self.playing:
            self.voice.stop()

    def after(self, _=None):
        if self.user_queue:
            self.djs.append(self.dj)
        fut = asyncio.run_coroutine_threadsafe(self.play_next_song(), self.loop)
        fut.result()

    async def play_next_song(self):
        if self.playing or not self.voice:
            return

        self.skip_votes.clear()
        try:
            await self.next_song()
        except ExtractionError:
            # For now lets just silently continue in the queue
            # Implementation to the music notifications channel will change what we do here
            return await self.play_next_song()

        if self.playing or not self.voice:
            return
        if self.current:
            source = FFmpegPCMAudio(
                self.current.filename,
                before_options='-nostdin',
                options='-vn -b:a 128k'
            )
            source = PCMVolumeTransformer(source, volume=self.volume)
            self.voice.play(source, after=self.after)
            self.current.start_time = time.time()
            # We handle users who join a user queue without songs (either at all, or ready) elsewhere
            # So if self.current is None here, there are a few reasons:
            # User queue, last song failed to download
            # Either queue, all songs/dj's have gone been gone through
            # The first one sucks, but there's not much we can do about it here, blame youtube
            # Second one just means we're done and don't want to do anything
            # So in either case....we simply do nothing here, and just the playing end

    async def next_song(self):
        if not self.user_queue:
            _result = await self.songs.get_next_entry()
            if _result:
                fut, self.current = _result
                if fut.exception():
                    raise ExtractionError(fut.exception())
            else:
                self.current = None
        else:
            try:
                dj = self.djs.popleft()
            except IndexError:
                self.dj = None
                self.current = None
            else:
                _result = await dj.get_next_entry()
                if _result:
                    fut, song = _result
                else:
                    return await self.next_song()
                if fut.exception():
                    raise ExtractionError(fut.exception())
                # Add an extra check here in case in the very short period of time possible, someone has queued a
                # song while we are downloading the next...which caused 2 play calls to be done
                # The 2nd may be called while the first has already started playing...this check is for that 2nd one
                # If this rare case does happen, we want to insert this dj back into the deque at the front
                # Also rotate their songs back, since it shouldn't have been retrieved
                if self.playing:
                    self.djs.insert(0, dj)
                    dj.entries.rotate()
                    return

                if song is None:
                    return await self.next_song()
                else:
                    song.requester = dj.member
                    self.dj = dj
                    self.current = song


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

    async def queue_embed_task(self, state, channel, author):
        index = 0
        message = None
        fmt = None
        possible_reactions = ['\u27A1', '\u2B05', '\u2b06', '\u2b07', '\u274c', '\u23ea', '\u23e9']

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
            if state.user_queue:
                queue = state.djs
            else:
                queue = state.songs.entries
            count = len(queue)
            # This means the last song was removed
            if count == 0:
                await channel.send("Nothing currently in the queue")
                break
            # Get the current entry
            entry = queue[index]
            dj = None
            if state.user_queue:
                dj = entry
                entry = entry.peek()
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
                if not author.guild_permissions.mute_members and author.id != entry.requester.id:
                    try:
                        await message.remove_reaction('\u274c', channel.server.me)
                    except:
                        pass
                elif not author.guild_permissions.mute_members and author.id == entry.requester.id:
                    try:
                        await message.add_reaction('\u274c')
                    except:
                        pass
            else:
                message = await channel.send(embed=embed)
                await message.add_reaction('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}')
                await message.add_reaction('\N{LEFTWARDS BLACK ARROW}')
                await message.add_reaction('\N{BLACK RIGHTWARDS ARROW}')
                await message.add_reaction('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}')
                # The moderation tools that can be used
                if author.guild_permissions.mute_members:
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
                if author.guild_permissions.mute_members and index > 0:
                    if dj and dj != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    elif not dj and entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Remove the current entry
                        del queue[index]
                        # Add it one position higher
                        if state.user_queue:
                            queue.insert(index - 1, dj)
                        else:
                            queue.insert(index - 1, entry)
                        # Lets move the index to look at the new place of the entry
                        index -= 1
            # If down is clicked
            elif '\u2b07' in reaction.emoji:
                # A second check just to make sure, as well as ensuring index is lower than last
                if author.guild_permissions.mute_members and index < (count - 1):
                    if dj and dj != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    elif not dj and entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Remove the current entry
                        del queue[index]
                        # Add it one position lower
                        if state.user_queue:
                            queue.insert(index + 1, dj)
                        else:
                            queue.insert(index + 1, entry)
                        # Lets move the index to look at the new place of the entry
                        index += 1
            # If x is clicked
            elif '\u274c' in reaction.emoji:
                # A second check just to make sure
                if author.guild_permissions.mute_members or author == entry.requester:
                    if dj and dj != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    elif not dj and entry != queue[index]:
                        fmt = "`Error: Position of this entry has changed, cannot complete your action`"
                    else:
                        # Simply remove the entry in place
                        del queue[index]
                        # This is the only check we need to make, to ensure index is now not more than last
                        new_count = count - 1
                        if index >= new_count:
                            index = new_count - 1
            # If first is clicked
            elif '\u23ea':
                index = 0
            # If last is clicked
            elif '\u23e9':
                index = count - 1
            try:
                await message.remove_reaction(reaction.emoji, user)
            except discord.Forbidden:
                pass
        await message.delete()

    # noinspection PyUnusedLocal
    async def on_voice_state_update(self, _, __, after):
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
        entry, _ = await state.songs.add_entry(song)
        if not state.playing:
            await state.play_next_song()
        entry.requester = ctx.message.author
        return entry

    async def join_channel(self, channel, text_channel):
        state = self.voice_states.get(channel.guild.id)
        log.info("Joining channel {} in guild {}".format(channel.id, channel.guild.id))

        # Send a message letting the channel know we are attempting to join
        try:
            msg = await text_channel.send("Trying to join channel {}...".format(channel.name))
        except discord.Forbidden:
            msg = None

        try:
            # If we're already connected, try moving to the channel
            if state and state.voice and state.voice.channel:
                await state.voice.move_to(channel)
            # Otherwise, try connecting
            else:
                await channel.connect()

            # If we have connnected, create our voice state
            queue_type = self.bot.db.load('server_settings', key=channel.guild.id, pluck='queue_type')
            user_queue = queue_type == "user"
            self.voice_states[channel.guild.id] = VoiceState(channel.guild, self.bot, user_queue=user_queue)

            # If we can send messages, edit it to let the channel know we have succesfully joined
            if msg:
                try:
                    await msg.edit(content="Ready to play audio in channel {}".format(channel.name))
                except discord.NotFound:
                    pass
            return True
        # If we time out trying to join, just let them know and return False
        except (asyncio.TimeoutError, OSError):
            if msg:
                try:
                    await msg.edit(content="Sorry, but I couldn't connect right now! Please try again later")
                except discord.NotFound:
                    pass
            return False
        # Theoretically this should never happen, however in rare cirumstances it does
        # This error arises when we are already in a channel and don't use "move"
        # We already checked if that existed above though, so this means the voice connection got stuck somewhere
        except discord.ClientException:
            if channel.guild.voice_client:
                # Force a disconnection
                await channel.guild.voice_client.disconnect(force=True)
                # Log this so we can track it
                log.warning(
                    "Force cleared voice connection on guild {} after being stuck "
                    "between connected/not connected".format(channel.guild.id))
                # Let them know what happened
                await text_channel.send("Sorry but I couldn't connect...try again?")
                return False

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def progress(self, ctx):
        """Provides the progress of the current song"""

        # Make sure we're playing first
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing or state.current is None:
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
    @utils.check_restricted()
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

        return await self.join_channel(channel, ctx.channel)

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def play(self, ctx, *, song: str):
        """Plays a song.
        If there is a song currently in the queue, then it is
        queued until the next song is done playing.
        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """
        # If we don't have a voice state yet, create one
        if ctx.message.guild.id not in self.voice_states:
            if not await ctx.invoke(self.join):
                return

        # If this is a user queue, this is the wrong command
        if self.voice_states.get(ctx.message.guild.id).user_queue:
            await ctx.send("The current queue type is the DJ queue. "
                           "Use the command {}dj to join this queue".format(ctx.prefix))
            return
        # Ensure the user is in the voice channel
        try:
            if ctx.message.author.voice.channel != ctx.message.guild.me.voice.channel:
                await ctx.send("You need to be in the channel to use this command!")
        except AttributeError:
                await ctx.send("You need to be in the channel to use this command!")

        song = re.sub('[<>\[\]]', '', song)
        if len(song) == 11:
            # Youtube-dl will attempt to use results with a length of 11 as a video ID
            # If this is a search, this causes it to break
            # Youtube will still succeed if this *is* an ID provided, if there's a . after
            song += "."

        try:
            entry = await self.add_entry(song, ctx)
        except LiveStreamError as e:
            await ctx.send(str(e))
        except WrongEntryTypeError:
            await ctx.send("Cannot enqueue playlists at this time.")
        except ExtractionError as e:
            error = e.message.split('\n')
            if len(error) >= 3:
                # The first entry is the "We couldn't download" printed by the exception
                # The 2nd is the new line
                # We want youtube_dl's error message, but just the first part, the actual "error"
                error = error[2]
                # This is colour formatting for the console...it's just going to show up as text on discord
                error = error.replace("[0;31mERROR:[0m ", "")
            else:
                # This happens when the download just returns `None`
                error = error[0]
            await ctx.send(error)
        else:
            try:
                if entry is None:
                    await ctx.send("Sorry but I couldn't download/find {}".format(song))
                else:
                    embed = entry.to_embed()
                    embed.title = "Enqueued song!"
                    await ctx.send(embed=embed)
            except discord.Forbidden:
                pass

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def volume(self, ctx, value: int = None):
        """Sets the volume of the currently playing song."""

        state = self.voice_states.get(ctx.message.guild.id)
        if value:
            value /= 100
        if state is None or state.voice is None:
            await ctx.send("I need to be in a channel before my volume can be set")
        elif value is None:
            await ctx.send('Current volume is {:.0%}'.format(state.volume))
        elif value > 1.0:
            await ctx.send("Sorry but the max volume is 100%")
        else:
            state.volume = value
            await ctx.send('Set the volume to {:.0%}'.format(state.volume))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.voice_states.get(ctx.message.guild.id)
        if state and state.voice and state.voice.is_connected():
            state.voice.pause()

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.voice_states.get(ctx.message.guild.id)
        if state and state.voice and state.voice.is_connected():
            state.voice.resume()

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        state = self.voice_states.get(ctx.message.guild.id)
        voice = ctx.message.guild.voice_client

        # If we have a state, clear the songs, dj's, then skip the current song
        if state:
            state.songs.clear()
            state.djs.clear()
            state.skip()
            try:
                del self.voice_states[ctx.message.guild.id]
            except KeyError:
                pass

        # If we have a voice connection (separate from state...just in case....)
        # Then stop playing, and disconnect
        if voice:
            voice.stop()
            await voice.disconnect()

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play"""
        state = self.voice_states.get(ctx.message.guild.id)
        author = ctx.message.author

        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return

        if state.user_queue:
            queue = [x.peek() for x in state.djs if x.peek()]
        else:
            queue = state.songs.entries
        if len(queue) == 0:
            await ctx.send("Nothing currently in the queue")
            return

        # Start off by adding the remaining length of the current song
        count = state.current.remaining or 0
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

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None:
            await ctx.send("Nothing currently in the queue")
            return

        if state.user_queue:
            _queue = [x.peek() for x in state.djs if x.peek()]
        else:
            _queue = state.songs.entries
        if len(_queue) == 0:
            await ctx.send("Nothing currently in the queue")
        else:
            self.bot.loop.create_task(self.queue_embed_task(state, ctx.message.channel, ctx.message.author))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None:
            await ctx.send("Nothing currently in the queue")
            return

        if state.user_queue:
            _queue = [x.peek() for x in state.djs if x.peek()]
        else:
            _queue = state.songs.entries
        if len(_queue) == 0:
            await ctx.send("Nothing currently in the queue")
        await ctx.send("There are a total of {} songs in the queue".format(len(_queue)))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.
        approximately 1/3 of the members in the voice channel
        are required to vote to skip for the song to be skipped.
        """

        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return
        # Ensure the user is in our channel
        try:
            if ctx.message.author.voice.channel != ctx.message.guild.me.voice.channel:
                await ctx.send("You need to be in the channel to use this command!")
        except AttributeError:
                await ctx.send("You need to be in the channel to use this command!")

        # Check if the person requesting a skip is the requester of the song, if so automatically skip
        voter = ctx.message.author
        if hasattr(state.current, 'requester') and voter == state.current.requester:
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

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing:
            await ctx.send('Not playing any music right now...')
            return

        state.skip()
        await ctx.send('Song has just been skipped.')

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.voice_states.get(ctx.message.guild.id)
        if state is None or not state.playing or not state.current:
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
            length = state.current.length
            progress = state.current.progress
            if length and progress:
                progress = divmod(round(progress, 0), 60)
                length = divmod(round(length, 0), 60)
                fmt = "{0[0]}m {0[1]}s/{1[0]}m {1[1]}s".format(progress, length)
                embed.add_field(name='Progress', value=fmt, inline=False)
                # And send the embed
                await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def dj(self, ctx):
        """Attempts to join the current DJ queue

        EXAMPLE: !dj
        RESULT: You are 7th on the waitlist for the queue"""
        if ctx.message.guild.id not in self.voice_states:
            if not await ctx.invoke(self.join):
                return

        state = self.voice_states.get(ctx.message.guild.id)
        if not state.user_queue:
            await ctx.send("The current queue type is the song queue. "
                           "Use the command {}play to add a song to the queue".format(ctx.prefix))
            return

        if state.get_dj(ctx.message.author):
            await ctx.send("You are already in the DJ queue!")
        else:
            new_dj = self.bot.get_cog('DJEvents').djs[ctx.message.author.id]
            if not new_dj.peek():
                await ctx.send("You currently have nothing in your playlist! This can happen for two reasons:\n"
                               "1) You actually have nothing in your active playlist\n"
                               "2) You just joined the voice channel and your playlist is still being downloaded\n\n"
                               "If the first one is true, then you need to manage your playlist to have an active "
                               "playlist with songs in it. "
                               "Otherwise, you will need to wait while your songs are being downloaded before you can "
                               "join")
            else:
                state.djs.append(new_dj)
                try:
                    await ctx.send("You have joined the DJ queue; there are currently {} people ahead of you".format(
                        state.djs.index(new_dj)))
                except discord.Forbidden:
                    pass

                if not state.playing:
                    await state.play_next_song()

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(mute_members=True)
    @utils.check_restricted()
    async def shuffle(self, ctx):
        """Shuffles the current playlist, be it users or songs

        EXAMPLE: !shuffle
        RESULT: The queue is shuffled"""
        state = self.voice_states.get(ctx.message.guild.id)
        if state:
            if state.user_queue:
                random.SystemRandom().shuffle(state.djs)
            else:
                state.songs.shuffle()
            await ctx.send("The queue has been shuffled!")
        else:
            await ctx.send("There needs to be a queue before I can shuffle it!")


def setup(bot):
    bot.add_cog(Music(bot))
