import aiohttp
import asyncio
import discord

from discord.ext import commands
from .utils import config
from .utils import checks


class Deviantart:
    def __init__(self, bot):
        self.base_url = "https://www.deviantart.com/api/v1/oauth2/gallery/all"
        self.bot = bot
        self.headers = {"User-Agent": config.user_agent}
        self.session = aiohttp.ClientSession()
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
        params = {'client_id': config.da_id,
                  'client_secret': config.da_secret,
                  'grant_type': 'client_credentials'}

        async with self.session.get(url, headers=self.headers, params=params) as response:
            data = await response.json()
            self.token = data.get('access_token', None)
            self.params = {'access_token': self.token}
            # Make sure we refresh our token, based on when they tell us it expires
            # Ensure we call it a few seconds earlier, to give us enough time to set the new token
            # If there was an issue, lets call this in a minute again
            return data.get('expires_in', 65) - 5

    async def check_posts(self):
        content = await config.get_content('deviantart')
        # People might sub to the same person, so lets cache every person and their last update
        cache = {}

        for entry in content:
            user = discord.utils.get(self.bot.get_all_members(), id=entry['member_id'])

            # If we're sharded, we might not be able to find this user.
            # If the bot is not in the server with the member either
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
                    async with self.session.get(self.base_url, headers=self.headers, params=params) as response:
                        data = await response.json()
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
                        await self.bot.send_message(user, fmt)
                    # Now we can update the user's last updated for this DA
                    # We want to do this whether or not our last if statement was met
                    r_filter = {'member_id': user.id}
                    update = {'last_updated': {da_name: result['deviationid']}}
                    await config.update_content('deviantart', update, r_filter)

    @commands.group()
    @checks.custom_perms(send_messages=True)
    async def da(self):
        """This provides a sort of 'RSS' feed for subscribed to artists.
        Subscribe to artists, and I will PM you when new posts come out from these artists"""
        pass

    @da.command(pass_context=True, name='sub', aliases=['add', 'subscribe'])
    @checks.custom_perms(send_messages=True)
    async def da_sub(self, ctx, *, username):
        """This can be used to add a feed to your notifications.
        Provide a username, and when posts are made from this user, you will be notified"""
        r_filter = {'member_id': ctx.message.author.id}
        content = await config.get_content('deviantart', r_filter)
        # TODO: Ensure the user provided is a real user

        if content is None:
            entry = {'member_id': ctx.message.author.id, 'subbed': [username], 'last_updated': {}}
            await config.add_content('deviantart', entry, r_filter)
            await self.bot.say("You have just subscribed to {}!".format(username))
        elif content[0]['subbed'] is None or username not in content[0]['subbed']:
            if content[0]['subbed'] is None:
                sub_list = [username]
            else:
                content[0]['subbed'].append(username)
                sub_list = content[0]['subbed']
            await config.update_content('deviantart', {'subbed': sub_list}, r_filter)
            await self.bot.say("You have just subscribed to {}!".format(username))
        else:
            await self.bot.say("You are already subscribed to that user!")

    @da.command(pass_context=True, name='unsub', aliases=['delete', 'remove', 'unsubscribe'])
    @checks.custom_perms(send_messages=True)
    async def da_unsub(self, ctx, *, username):
        """This command can be used to unsub from the specified user"""
        r_filter = {'member_id': ctx.message.author.id}
        content = await config.get_content('deviantart', r_filter)

        if content is None or content[0]['subbed'] is None:
            await self.bot.say("You are not subscribed to anyone at the moment!")
        elif username in content[0]['subbed']:
            content[0]['subbed'].remove(username)
            await config.update_content('deviantart', {'subbed': content[0]['subbed']}, r_filter)
            await self.bot.say("You have just unsubscribed from {}!".format(username))
        else:
            await self.bot.say("You are not subscribed to that user!")


def setup(bot):
    bot.add_cog(Deviantart(bot))
