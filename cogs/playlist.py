import discord
import asyncio
from discord.ext import commands

from . import utils


class Playlist:
    """Used to manage user playlists"""

    def __init__(self, bot):
        self.bot = bot

    async def get_response(self, ctx, question):
        # Save our simple variables
        channel = ctx.message.channel
        author = ctx.message.author

        # Create our check function used to ensure the author and channel are the only possible message we get
        check = lambda m: m.author == author and m.channel == channel

        try:
            # Ask our question, wait 60 seconds for a response
            my_msg = await ctx.send(question)
            response = await self.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            # If we timeout, let them know and return None
            await ctx.send("You took too long. I'm impatient, don't make me wait")
            return None
        else:
            # If succesful try to delete the message we sent, and the response
            try:
                await my_msg.delete()
                await response.delete()
            except discord.Forbidden:
                pass

            # For our case here, everything needs to be lowered and stripped, so just do this now
            return response.content.lower().strip()

    async def get_info(self, song_url):
        try:
            # Just download the information
            info = await self.bot.downloader.extract_info(self.bot.loop, song_url, download=False)
        except Exception as e:
            # If we fail, it's possibly due to an incorrect detection as a URL instead of a search
            if "gaierror" in str(e) or "unknown url type" in str(e):
                # So just force a search
                song_url = "ytsearch:" + song_url
                info = await self.bot.downloader.extract_info(self.bot.loop, song_url, download=False)
            else:
                # Otherwise if we fail, we just want to return None
                return None

        # If we detected a search, get the first entry in the results
        if info.get('_type', None) == 'playlist':
            if info.get('extractor') == 'youtube:search':
                if len(info['entries']) == 0:
                    return None
                else:
                    info = info['entries'][0]
                    song_url = info['webpage_url']

        # If we are successful, create the entry we'll need to add to the playlist database, and return it
        if info:
            return {
                'title': info.get('title', 'Untitled'),
                'url': song_url
            }
        else:
            return None

    async def add_to_playlist(self, author, playlist, url):
        # Simply get the database entry for this user's playlist
        key = str(author.id)
        playlist = playlist.lower().strip()
        playlists = self.bot.db.load('user_playlists', key=key, pluck='playlists') or []

        entry = await self.get_info(url)

        # Search through, find the name that matches the playlist
        if entry:
            for pl in playlists:
                if pl['name'] == playlist:
                    # If we find it, add the song entry to the songs
                    pl['songs'].append(entry)
                    # Create the json needed to save to the database, and save
                    update = {
                        'member_id': key,
                        'playlists': playlists
                    }
                    self.bot.db.save('user_playlists', update)
                    return True

    async def rename_playlist(self, author, old_name, new_name):
        # Simply get the database entry for this user's playlist
        key = str(author.id)
        old_name = old_name.lower().strip()
        new_name = new_name.lower().strip()
        playlists = self.bot.db.load('user_playlists', key=key, pluck='playlists') or []

        # Find the playlist that matches the old name
        for pl in playlists:
            if pl['name'] == old_name:
                # Once found, change the name, update the json, save
                pl['name'] = new_name
                update = {
                    'member_id': key,
                    'playlists': playlists
                }
                self.bot.db.save('user_playlists', update)
                return True

    async def remove_from_playlist(self, author, playlist, index):
        # Simply get the database entry for this user's playlist
        key = str(author.id)
        playlist = playlist.lower().strip()
        playlists = self.bot.db.load('user_playlists', key=key, pluck='playlists') or []

        # Loop through till we find the playlist that matches
        for pl in playlists:
            if pl['name'] == playlist:
                song = pl['songs'][index]
                # Once found, remove the matching song, update json, save
                pl['songs'].remove(song)
                update = {
                    'member_id': key,
                    'playlists': playlists
                }
                self.bot.db.save('user_playlists', update)
                return song

    async def update_dj_for_member(self, member):
        music = self.bot.get_cog('Music')
        if music:
            for state in music.voice_states.values():
                dj = state.get_dj(member)
                if dj:
                    # We want to add a slight delay to this, because our database method launches a task to update
                    # Before we update what is live, we need the information saved in (at least the cache) the database
                    await asyncio.sleep(2)
                    self.bot.loop.create_task(dj.resolve_playlist())

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def playlists(self, ctx):
        """Displays the playlists you have

        EXAMPLE: !playlists
        RESULT: All your playlists"""
        # Get all the author's playlists
        playlists = self.bot.db.load('user_playlists', key=ctx.message.author.id, pluck='playlists')
        if playlists:
            # Create the entries for our paginator detailing the name of the playlist, and the number of songs in it
            entries = [
                "{} ({} songs)".format(x['name'], len(x['songs'])) if not x.get('active')
                else "{} ({} songs) - Active playlist".format(x['name'], len(x['songs']))
                for x in playlists
                ]

            try:
                # And paginate
                pages = utils.Pages(self.bot, message=ctx.message, entries=entries)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))
        else:
            await ctx.send("You do not have any playlists")

    @commands.group(invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def playlist(self, ctx, *, playlist_name):
        """Used to view your playlists

        EXAMPLE: !playlist Playlist 2
        RESULT: Displays the songs in your playlist called "Playlist 2" """
        playlist_name = playlist_name.lower().strip()

        playlists = self.bot.db.load('user_playlists', key=ctx.message.author.id, pluck='playlists')
        try:
            # Get the playlist if the name matches
            playlist = [x for x in playlists if playlist_name == x['name']][0]
            # Create the entries for our paginator just based on the title of the songs in the playlist
            entries = ["{}".format(x['title']) for x in playlist['songs']]
            # Paginate
            pages = utils.Pages(self.bot, message=ctx.message, entries=entries)
            await pages.paginate()
        except (IndexError, TypeError, KeyError):
            await ctx.send("You do not have a playlist named {}!".format(playlist_name))
        except utils.CannotPaginate as e:
            await ctx.send(str(e))

    @playlist.command(name='create')
    @utils.custom_perms(send_messages=True)
    async def _pl_create(self, ctx, *, name):
        """Used to create a new playlist

        EXAMPLE: !playlist create Playlist
        RESULT: A new playlist called Playlist"""
        key = str(ctx.message.author.id)
        playlists = self.bot.db.load('user_playlists', key=key, pluck='playlists') or []

        # Create the new playlist entry
        entry = {
            'name': name.lower().strip(),
            'songs': []
        }

        # Check to make sure that there isn't a playlist with the same name
        names = [x['name'] for x in playlists]
        if name in names:
            await ctx.send('You already have a playlist called {}'.format(name))
        # Otherwise add this new playlist, and save
        else:
            # This is here to set the first playlist we create as the active one.
            # If someone has a playlist already, we don't want to change which is the active one
            # If they don't have any, then we want to set our first one as the active one
            entry['active'] = len(playlists) == 0
            playlists.append(entry)
            update = {
                'member_id': key,
                'playlists': playlists
            }
            self.bot.db.save('user_playlists', update)
            await ctx.send("You have just created a new playlist called {}".format(name))

    @playlist.command(name='edit')
    @utils.custom_perms(send_messages=True)
    async def _pl_edit(self, ctx):
        """A command used to edit a current playlist
        The available ways to edit a playlist are to rename, add a song, remove a song, or delete the playlist

        EXAMPLE: !playlist edit
        RESULT: A followalong asking for what you need"""
        # Load the playlists for the author
        key = str(ctx.message.author.id)
        playlists = self.bot.db.load('user_playlists', key=key, pluck='playlists') or []
        # Also create a list of the names for easy comparision
        names = [x['name'] for x in playlists]

        if not playlists:
            await ctx.send("You have no playlists to edit!")
            return

        # Show the playlists we have, and ask which to choose from
        await ctx.invoke(self.playlists)
        question = "Please provide what playlist you would like to edit, the playlists you have available are above."
        playlist = await self.get_response(ctx, question)
        if not playlist:
            return
        if playlist not in names:
            await ctx.send("You do not have a playlist named {}!".format(playlist))
            return

        q1 = "How would you like to edit {}? Choices are `add`, `remove`, `rename`, `delete`, or `activate`.\n" \
             "**add** - Adds a song to this playlist\n" \
             "**remove** - Removes a song from this playlist\n" \
             "**rename** - Changes the name of this playlist\n" \
             "**delete** - Deletes this playlist\n" \
             "**activate** - Sets this as the active playlist\n\n" \
             "Type **quit** to stop editing this playlist".format(playlist)

        # Lets create a list of the messages we'll delete after
        delete_msgs = []

        # We want to loop this in order to continue editing, till the user is done
        while True:
            response = await self.get_response(ctx, q1)

            if not response:
                break

            if 'add' in response:
                # Ask the user what song to add, get the response, add it
                question = "What is the song you would like to add to {}?".format(playlist)
                response = await self.get_response(ctx, question)
                # If we didn't get a response, just continue with the loop, we have no need to say anything
                # The "error" message is sent with our `get_response` helper method
                if response:
                    await ctx.message.channel.trigger_typing()
                    await self.add_to_playlist(ctx.message.author, playlist, response)
                    delete_msgs.append(await ctx.send("Successfully added song {} to playlist {}".format(response,
                                                                                                         playlist)))
            elif 'remove' in response:
                await ctx.invoke(self.playlist, playlist_name=playlist)
                question = "Please provide just the number of the song you want to delete"
                try:
                    response = await self.get_response(ctx, question)
                    if response:
                        num = int(response) - 1
                        song = await self.remove_from_playlist(ctx.author, playlist, num)
                        await ctx.send("Successfully removed {} from {}".format(song['title'], playlist))
                except (ValueError, IndexError):
                    delete_msgs.append(await ctx.send("Please provide just the number of the song you want to delete "
                                                      "next time!"))
            elif 'delete' in response:
                playlists = [x for x in playlists if x['name'] != playlist]
                entry = {
                    'member_id': str(key),
                    'playlists': playlists
                }
                self.bot.db.save('user_playlists', entry)
                delete_msgs.append(await ctx.send("Successfully deleted playlist {}".format(playlist)))
                await ctx.send("Finished editing {}".format(playlist))
                break
            elif 'rename' in response:
                question = "What would you like to rename the playlist {} to?".format(playlist)
                new_name = await self.get_response(ctx, question)
                if new_name:
                    await self.rename_playlist(ctx.message.author, playlist, new_name)
                    playlist = new_name
                    delete_msgs.append(await ctx.send("Successfully renamed {} to {}!".format(playlist, new_name)))
            elif 'activate' in response:
                for x in playlists:
                    x['active'] = x['name'] == playlist

                entry = {
                    'member_id': str(key),
                    'playlists': playlists
                }
                self.bot.db.save('user_playlists', entry)
                # Now we have edited the user's actual playlist...but we need to
                delete_msgs.append(await ctx.send("{} is now your active playlist".format(playlist)))
            elif 'quit' in response:
                await ctx.send("Finished editing {}".format(playlist))
                break
            else:
                delete_msgs.append(await ctx.send("That is not a valid option!"))

            # After whatever has been edited, we need to update the live DJ's
            await self.update_dj_for_member(ctx.message.author)

        if len(delete_msgs) == 1:
            await delete_msgs[0].delete()
        elif len(delete_msgs) > 1:
            await ctx.message.channel.delete_messages(delete_msgs)


def setup(bot):
    bot.add_cog(Playlist(bot))
