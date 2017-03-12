import aiohttp
import asyncio
import discord
import traceback
import logging

from discord.ext import commands

from . import utils

log = logging.getLogger()


class Deviantart:
    def __init__(self, bot):
        self.base_url = "https://www.deviantart.com/api/v1/oauth2/gallery/all"
        self.bot = bot
        self.token = None
        self.params = None
        bot.loop.create_task(self.token_task())
        bot.loop.create_task(self.post_task())

    async def token_task(self):
        while True:
            expires_in = await self.get_token()
            await asyncio.sleep(expires_in)

    async def post_task(self):
        await asyncio.sleep(5)
        # Lets start the task a few seconds after, to ensure our token gets set
        while True:
            await self.check_posts()
            await asyncio.sleep(300)

    async def get_token(self):
        # We need a token to create requests, it doesn't seem this token goes away
        # To get this token, we need to make a request and retrieve that
        url = 'https://www.deviantart.com/oauth2/token'
        params = {'client_id': utils.da_id,
                  'client_secret': utils.da_secret,
                  'grant_type': 'client_credentials'}

        data = await utils.request(url, payload=params)

        self.token = data.get('access_token', None)
        self.params = {'access_token': self.token}
        # Make sure we refresh our token, based on when they tell us it expires
        # Ensure we call it a few seconds earlier, to give us enough time to set the new token
        # If there was an issue, lets call this in a minute again
        return data.get('expires_in', 65) - 5

    async def check_posts(self):
        content = await utils.get_content('deviantart')
        # People might sub to the same person, so lets cache every person and their last update
        cache = {}

        if not content:
            return

        try:
            for entry in content:
                user = discord.utils.get(self.bot.get_all_members(), id=entry['member_id'])
                # If the bot is not in the server with the member, we might not be able to find this user.
                if user is None:
                    continue

                params = self.params.copy()
                # Now loop through the subscriptions
                for da_name in entry['subbed']:
                    # Check what the last updated content we sent to this user was
                    # Since we cannot go back in time, if this doesn't match the last uploaded from the user
                    # Assume we need to notify the user of this post
                    last_updated_id = entry['last_updated'].get(da_name, None)
                    # Check if this user has been requested already, if so we don't need to make another request
                    result = cache.get(da_name, None)
                    if result is None:
                        params['username'] = da_name
                        data = await utils.request(self.base_url, payload=params)
                        if data is None:
                            continue
                        elif not data['results']:
                            continue

                        result = data['results'][0]
                        cache[da_name] = result

                    # This means that our last update to this user, for this author, is not the same
                    if last_updated_id != result['deviationid']:
                        # First lets check if the last updated ID was None, if so...then we haven't alerted them yet
                        # We don't want to alert them in this case
                        # We just want to act like the artist's most recent update was the last notified
                        # So just notify the user if this is not None
                        if last_updated_id is not None:
                            fmt = "There has been a new post by an artist you are subscribed to!\n\n" \
                                  "**Title:** {}\n**User:** {}\n**URL:** {}".format(
                                    result['title'],
                                    result['author']['username'],
                                    result['url'])
                            await user.send(fmt)
                        # Now we can update the user's last updated for this DA
                        # We want to do this whether or not our last if statement was met
                        update = {'last_updated': {da_name: result['deviationid']}}
                        await utils.update_content('deviantart', update, str(user.id))
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group()
    @utils.custom_perms(send_messages=True)
    async def da(self, ctx):
        """This provides a sort of 'RSS' feed for subscribed to artists.
        Subscribe to artists, and I will PM you when new posts come out from these artists"""
        pass

    @da.command(name='sub', aliases=['add', 'subscribe'])
    @utils.custom_perms(send_messages=True)
    async def da_sub(self, ctx, *, username):
        """This can be used to add a feed to your notifications.
        Provide a username, and when posts are made from this user, you will be notified

        EXAMPLE: !da sub MyFavoriteArtistEva<3
        RESULT: Notifications of amazing pics c:"""
        key = str(ctx.message.author.id)
        content = await utils.get_content('deviantart', key)
        # TODO: Ensure the user provided is a real user

        if content is None:
            entry = {'member_id': str(ctx.message.author.id), 'subbed': [username], 'last_updated': {}}
            await utils.add_content('deviantart', entry)
            await ctx.send("You have just subscribed to {}!".format(username))
        elif content['subbed'] is None or username not in content['subbed']:
            if content['subbed'] is None:
                sub_list = [username]
            else:
                content['subbed'].append(username)
                sub_list = content['subbed']
            await utils.update_content('deviantart', {'subbed': sub_list}, key)
            await ctx.send("You have just subscribed to {}!".format(username))
        else:
            await ctx.send("You are already subscribed to that user!")

    @da.command(name='unsub', aliases=['delete', 'remove', 'unsubscribe'])
    @utils.custom_perms(send_messages=True)
    async def da_unsub(self, ctx, *, username):
        """This command can be used to unsub from the specified user

        EXAMPLE: !da unsub TheArtistWhoBetrayedMe
        RESULT: No more pics from that terrible person!"""
        key = (ctx.message.author.id)
        content = await utils.get_content('deviantart', key)

        if content is None or content['subbed'] is None:
            await ctx.send("You are not subscribed to anyone at the moment!")
        elif username in content['subbed']:
            content['subbed'].remove(username)
            await utils.update_content('deviantart', {'subbed': content['subbed']}, key)
            await ctx.send("You have just unsubscribed from {}!".format(username))
        else:
            await ctx.send("You are not subscribed to that user!")

    @da.command(name='list')
    @utils.custom_perms(send_messages=True)
    async def da_list(self, ctx):
        """Lists the artists you are subscribed to on DA

        EXAMPLE: !da list
        RESULT: Artist 1, Artist2, Artist 3"""

        key = str(ctx.message.author.id)
        content = await utils.get_content('deviantart', key)

        if content is None or content['subbed'] is None:
            await ctx.send("You are not subscribed to anyone at the moment!")
        else:
            fmt = ", ".join(content['subbed'])
            await ctx.send("You are subscribed to:\n\n{}".format(fmt))


def setup(bot):
    bot.add_cog(Deviantart(bot))
