from .voice_utilities import *

import discord
from discord.ext import commands

from . import utils

import math
import time
import asyncio
import re
import os
import glob
import socket
import inspect

if not discord.opus.is_loaded():
    discord.opus.load_opus('/usr/lib64/libopus.so.0')


class VoiceState:
    def __init__(self, bot, download):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        # This is the queue that holds all VoiceEntry's
        self.songs = Playlist(bot)
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
        self.downloader = download
        self.file_names = []

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
            # Now wait for the next song in the queue
            self.current = await self.songs.get_next_entry()

            # Make sure we find a song
            while self.current is None:
                self.clear_audio_files()
                await asyncio.sleep(1)
                self.current = await self.songs.get_next_entry()

            # At this point we're sure we have a song, however it needs to be downloaded
            while not getattr(self.current, 'filename'):
                print("Downloading...")
                await asyncio.sleep(1)

            # Now add this file to our list of filenames, so that it can be deleted later
            if self.current.filename not in self.file_names:
                self.file_names.append(self.current.filename)

            # Create the player object
            self.current.player = self.voice.create_ffmpeg_player(
                self.current.filename,
                before_options="-nostdin",
                options="-vn -b:a 128k",
                after=self.toggle_next
            )

            # Now we can start actually playing the song
            self.current.player.start()
            self.current.player.volume = self.volume / 100

            # Save the variable for when our time for this song has started
            self.current.start_time = time.time()

            # Wait till the Event has been set, before doing our task again
            await self.play_next_song.wait()

    def clear_audio_files(self):
        """Deletes all the audio files this guild has created"""
        for f in self.file_names:
            os.remove(f)
        self.file_names = []

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
        self.clear_audio_tmp()

    def clear_audio_tmp(self):
        files = glob.glob('audio_tmp/*')
        for f in files:
            os.remove(f)

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)

        # Internally handle creating a voice state if there isn't a current state
        # This can be used for example, in case something is skipped when not being connected
        # We create the voice state when checked
        # This only creates the state, we are still not playing anything, which can then be handled separately
        if state is None:
            state = VoiceState(self.bot, self.downloader)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        """Creates a voice client and saves it"""
        # First join the channel and get the VoiceClient that we'll use to save per server
        await self.remove_voice_client(channel.server)

        server = channel.server
        state = self.get_voice_state(server)
        voice = self.bot.voice_client_in(server)
        # Attempt 3 times
        for i in range(3):
            try:
                if voice is None:
                    state.voice = await self.bot.join_voice_channel(channel)
                    if state.voice:
                        return True
                elif voice.channel == channel:
                    state.voice = voice
                    return True
                else:
                    # This shouldn't theoretically ever happen yet it does. Thanks Discord
                    await voice.disconnect()
                    state.voice = await self.bot.join_voice_channel(channel)
                    if state.voice:
                        return True
            except (discord.ClientException, socket.gaierror, ConnectionResetError):
                continue

        return False


    async def remove_voice_client(self, server):
        """Removes any voice clients from a server
        This is sometimes needed, due to the unreliability of Discord's voice connection
        We do not want to end up with a voice client stuck somewhere, so this cancels any found for a server"""
        state = self.get_voice_state(server)
        voice = self.bot.voice_client_in(server)

        if voice:
            await voice.disconnect()
        if state.voice:
            await state.voice.disconnect()

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
        num_members = len(voice_channel.voice_members)
        state.required_skips = math.ceil((num_members + 1) / 3)

    async def queue_embed_task(self, state, channel, author):
        index = 0
        message = None
        fmt = None
        # Our check to ensure the only one who reacts is the bot
        def check(reaction, user):
            return user == author
        possible_reactions = ['\u27A1', '\u2B05', '\u2b06', '\u2b07', '\u274c']
        while True:
            # Get the current queue (It might change while we're doing this)
            # So do this in the while loop
            queue = state.songs.entries
            count = len(queue)
            # This means the last song was removed
            if count == 0:
                await self.bot.send_message(channel, "Nothing currently in the queue")
                break
            # Get the current entry
            entry = queue[index]
            # Get the entry's embed
            embed = entry.to_embed()
            # Set the embed's title to indicate the amount of things in the queue
            count = len(queue)
            embed.title = "Current Queue [{}/{}]".format(index+1, count)
            # Now we need to send the embed, so check if the message is already set
            # If not, then we need to send a new one (i.e. this is the first time called)
            if message:
                message = await self.bot.edit_message(message, fmt, embed=embed)
                # There's only one reaction we want to make sure we remove in the circumstances
                # If the member doesn't have kick_members permissions, and isn't the requester
                # Then they can't remove the song, otherwise they can
                if not author.server_permissions.kick_members and author != entry.requester:
                    try:
                        await self.bot.remove_reaction(message, '\u274c', channel.server.me)
                    except:
                        pass
                elif not author.server_permissions.kick_members and author == entry.requester:
                    try:
                        await self.bot.add_reaction(message, '\u274c')
                    except:
                        pass
            else:
                message = await self.bot.send_message(channel, embed=embed)
                await self.bot.add_reaction(message, '\N{LEFTWARDS BLACK ARROW}')
                await self.bot.add_reaction(message, '\N{BLACK RIGHTWARDS ARROW}')
                # The moderation tools that can be used
                if author.server_permissions.kick_members:
                    await self.bot.add_reaction(message, '\N{DOWNWARDS BLACK ARROW}')
                    await self.bot.add_reaction(message, '\N{UPWARDS BLACK ARROW}')
                    await self.bot.add_reaction(message, '\N{CROSS MARK}')
                elif author == entry.requester:
                    await self.bot.add_reaction(message, '\N{CROSS MARK}')
            # Reset the fmt message
            fmt = None
            # Now we wait for the next reaction
            res = await self.bot.wait_for_reaction(possible_reactions, message=message, check=check, timeout=180)
            if res is None:
                break
            else:
                reaction, user = res
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
                if author.server_permissions.kick_members and index > 0:
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
                if author.server_permissions.kick_members and index < (count - 1):
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
                if author.server_permissions.kick_members or author == entry.requester:
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
                await self.bot.remove_reaction(message, reaction.emoji, user)
            except discord.Forbidden:
                pass
        await self.bot.delete_message(message)

    @commands.command(pass_context=True)
    @commands.check(utils.is_owner)
    async def vdebug(self, ctx, *, code : str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'server': ctx.message.server,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await self.bot.say(python.format(type(e).__name__ + ': ' + str(e)))
            return

        await self.bot.say(python.format(result))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
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
            fmt = "Current song progress: {0[0]}m {0[1]}s/{1[0]}m {1[1]}s".format(progress, length)
            await self.bot.say(fmt)

    @commands.command(no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def join(self, *, channel: discord.Channel):
        """Joins a voice channel."""
        try:
            await self.create_voice_client(channel)
        # Check if the channel given was an actual voice channel
        except discord.InvalidArgument:
            await self.bot.say('This is not a voice channel...')
        except (asyncio.TimeoutError, discord.ConnectionClosed):
            await self.bot.say("I failed to connect! This usually happens if I don't have permission to join the"
                               " channel, but can sometimes be caused by your server region being far away."
                               " Otherwise this is an issue on Discord's end, causing the connect to timeout!")
            await self.remove_voice_client(channel.server)
        else:
            await self.bot.say('Ready to play audio in ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def summon(self, ctx):
        """Summons the bot to join your voice channel."""
        # This method will be invoked by other commands, so we should return True or False instead of just returning
        # First check if the author is even in a voice_channel
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('You are not in a voice channel.')
            return False

        # Then simply create a voice client
        try:
            success = await self.create_voice_client(summoned_channel)
        except (asyncio.TimeoutError, discord.ConnectionClosed):
            await self.bot.say("I failed to connect! This usually happens if I don't have permission to join the"
                               " channel, but can sometimes be caused by your server region being far away."
                               " Otherwise this is an issue on Discord's end, causing the connect to timeout!")
            await self.remove_voice_client(summoned_channel.server)
            return False

        if success:
            try:
                await self.bot.say('Ready to play audio in ' + summoned_channel.name)
            except discord.Forbidden:
                pass
        return success

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
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
        # Since summon utils if the author is in a channel, we don't need to handle that here, just return if it failed
        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        # If the queue is full, we ain't adding anything to it
        if state.songs.full:
            await self.bot.say("The queue is currently full! You'll need to wait to add a new song")
            return

        author_channel = ctx.message.author.voice.voice_channel
        my_channel = ctx.message.server.me.voice.voice_channel

        if my_channel is None:
            # If we're here this means that after 3 attempts...4 different "failsafes"...
            # Discord has returned saying the connection was successful, and returned a None connection
            await self.bot.say("I failed to connect to the channel! Please try again soon")
            return

        # To try to avoid some abuse, ensure the requester is actually in our channel
        if my_channel != author_channel:
            await self.bot.say("You are not currently in the channel; please join before trying to request a song.")
            return

        # Set the number of required skips to start
        num_members = len(my_channel.voice_members)
        state.required_skips = math.ceil((num_members + 1) / 3)

        # Create the player, and check if this was successful
        # Here all we want is to get the information of the player
        song = re.sub('[<>\[\]]', '', song)

        try:
            _entry, position = await state.songs.add_entry(song, ctx.message.author)
        except WrongEntryTypeError:
            # This means that a song was attempted to be searched, instead of a link provided
            try:
                info = await self.downloader.extract_info(self.bot.loop, song, download=False, process=True)
                song = info.get('entries', [])[0]['webpage_url']
            except IndexError:
                await self.bot.send_message(ctx.message.channel, "No results found for {}!".format(song))
                return
            except ExtractionError as e:
                # This gets the youtube_dl error, instead of our error raised
                error = str(e).split("\n\n")[1]
                # Youtube has a "fancy" colour error message it prints to the console
                # Obviously this doesn't work in Discord, so just remove this
                error = " ".join(error.split()[1:])
                await self.bot.send_message(ctx.message.channel, error)
                return
            try:
                _entry, position = await state.songs.add_entry(song, ctx.message.author)
            except WrongEntryTypeError:
                # This is either a playlist, or something not supported
                fmt = "Sorry but I couldn't download that! Either you provided a playlist, a streamed link, or " \
                      "a page that is not supported to download."
                await self.bot.send_message(ctx.message.channel, fmt)
                return
        except ExtractionError as e:
            # This gets the youtube_dl error, instead of our error raised
            error = str(e).split("\n\n")[1]
            # Youtube has a "fancy" colour error message it prints to the console
            # Obviously this doesn't work in Discord, so just remove this
            error = " ".join(error.split()[1:])
            # Make sure we are not over our 2000 message limit length (there are some youtube errors that are)
            if len(error) >= 2000:
                error = "{}...".format(error[:1996])
            await self.bot.send_message(ctx.message.channel, error)
            return
        await self.bot.say('Enqueued ' + str(_entry))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(kick_members=True)
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
    @utils.custom_perms(kick_members=True)
    async def pause(self, ctx):
        """Pauses the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            state.player.pause()

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(kick_members=True)
    async def resume(self, ctx):
        """Resumes the currently played song."""
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            state.player.resume()

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(kick_members=True)
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel.
        This also clears the queue.
        """
        server = ctx.message.server
        state = self.get_voice_state(server)

        # Stop playing whatever song is playing.
        if state.is_playing():
            state.player.stop()

        state.songs.clear()

        # This will stop cancel the audio event we're using to loop through the queue
        # Then erase the voice_state entirely, and disconnect from the channel
        try:
            state.audio_player.cancel()
            state.clear_audio_files()
            await self.remove_voice_client(ctx.message.server)
            del self.voice_states[server.id]
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def eta(self, ctx):
        """Provides an ETA on when your next song will play"""
        # Note: There is no way to tell how long a song has been playing, or how long there is left on a song
        # That is why this is called an "ETA"
        state = self.get_voice_state(ctx.message.server)
        author = ctx.message.author

        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        queue = state.songs.entries
        if len(queue) == 0:
            await self.bot.say("Nothing currently in the queue")
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

        # This is checking if nothing from the queue has been added to the total
        # If it has not, then we have not looped through the queue at all
        # Since the queue was already checked to have more than one song in it, this means the author is next
        if count == state.current.duration:
            await self.bot.say("You are next in the queue!")
            return
        if not found:
            await self.bot.say("You are not in the queue!")
            return
        await self.bot.say("ETA till your next play is: {0[0]}m {0[1]}s".format(divmod(round(count, 0), 60)))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def queue(self, ctx):
        """Provides a printout of the songs that are in the queue"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        # Asyncio provides no non-private way to access the queue, so we have to use _queue
        queue = state.songs.entries
        if len(queue) == 0:
            await self.bot.say("Nothing currently in the queue")
        else:
            self.bot.loop.create_task(self.queue_embed_task(state, ctx.message.channel, ctx.message.author))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def queuelength(self, ctx):
        """Prints the length of the queue"""
        await self.bot.say("There are a total of {} songs in the queue"
                           .format(len(self.get_voice_state(ctx.message.server).songs.entries)))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
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
    @utils.custom_perms(kick_members=True)
    async def modskip(self, ctx):
        """Forces a song skip, can only be used by a moderator"""
        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing any music right now...')
            return

        state.skip()
        await self.bot.say('Song has just been skipped.')

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def playing(self, ctx):
        """Shows info about the currently played song."""

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('Not playing anything.')
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
            embed.add_field(name='Progress', value=fmt,inline=False)
            # And send the embed
            await self.bot.say(embed=embed)


def setup(bot):
    bot.add_cog(Music(bot))
