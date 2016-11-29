from discord.ext import commands
from .utils import config
from .utils import checks

import aiohttp
import asyncio
import discord
import json
import re
import rethinkdb as r
import traceback
import logging

log = logging.getLogger()


class Twitch:
    """Class for some twitch integration
    You can add or remove your twitch stream for your user
    I will then notify the server when you have gone live or offline"""

    def __init__(self, bot):
        self.bot = bot
        self.key = config.twitch_key
        self.params = {'client_id': self.key}
        self.headers = {"User-Agent": config.user_agent,
                        "Client-ID": self.key}

    async def channel_online(self, channel: str):
        # Check a specific channel's data, and get the response in text format
        url = "https://api.twitch.tv/kraken/streams/{}".format(channel)
        with aiohttp.ClientSession() as s:
            async with s.get(url, headers=self.headers, params=self.params) as response:
                result = await response.text()

        # For some reason Twitch's API call is not reliable, sometimes it returns stream as None
        # That is what we're checking specifically, sometimes it doesn't exist in the returned JSON at all
        # Sometimes it returns something that cannot be decoded with JSON
        # In either error case, just assume they're offline, the next check will most likely work
        try:
            data = json.loads(result)
            return data['stream'] is not None
        except (KeyError, json.JSONDecodeError):
            return False

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # Loop through as long as the bot is connected
        try:
            while not self.bot.is_closed:
                twitch = await config.get_content('twitch', {'notifications_on': 1})
                # Online/offline is based on whether they are set to such, in the config file
                # This means they were detected as online/offline before and we check for a change
                online_users = {data['member_id']: data for data in twitch if data['live']}
                offline_users = {data['member_id']: data for data in twitch if not data['live']}
                for m_id, result in offline_users.items():
                    # Get their url and their user based on that url
                    url = result['twitch_url']
                    user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                    # Check if they are online right now
                    if await self.channel_online(user):
                        for server_id in result['servers']:
                            # Get the channel to send the message to, based on the saved alert's channel
                            server = self.bot.get_server(server_id)
                            if server is None:
                                continue
                            server_alerts = await config.get_content('server_alerts', {'server_id': server_id})
                            channel_id = server_id
                            if len(server_alerts) > 0:
                                channel_id = server_alerts[0].get('channel_id')
                            channel = self.bot.get_channel(channel_id)
                            # Get the member that has just gone live
                            member = discord.utils.get(server.members, id=m_id)

                            fmt = "{} has just gone live! View their stream at {}".format(member.display_name, url)
                            await self.bot.send_message(channel, fmt)
                        await config.update_content('twitch', {'live': 1}, {'member_id': m_id})
                for m_id, result in online_users.items():
                    # Get their url and their user based on that url
                    url = result['twitch_url']
                    user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                    # Check if they are online right now
                    if not await self.channel_online(user):
                        for server_id in result['servers']:
                            # Get the channel to send the message to, based on the saved alert's channel
                            server = self.bot.get_server(server_id)
                            if server is None:
                                continue
                            server_alerts = await config.get_content('server_alerts', {'server_id': server_id})
                            channel_id = server_id
                            if len(server_alerts) > 0:
                                channel_id = server_alerts[0].get('channel_id')
                            channel = self.bot.get_channel(channel_id)
                            # Get the member that has just gone live
                            member = discord.utils.get(server.members, id=m_id)
                            fmt = "{} has just gone offline! Catch them next time they stream at {}".format(
                                member.display_name, url)
                            await self.bot.send_message(channel, fmt)
                        await config.update_content('twitch', {'live': 0}, {'member_id': m_id})
                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def twitch(self, ctx, *, member: discord.Member = None):
        """Use this command to check the twitch info of a user

        EXAMPLE: !twitch @OtherPerson
        RESULT: Information about their twitch URL"""
        if member is None:
            member = ctx.message.author

        result = await config.get_content('twitch', {'member_id': member.id})
        if result is None:
            await self.bot.say("{} has not saved their twitch URL yet!".format(member.name))
            return

        result = result[0]
        url = result['twitch_url']
        user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
        twitch_url = "https://api.twitch.tv/kraken/channels/{}?client_id={}".format(user, self.key)
        with aiohttp.ClientSession() as s:
            async with s.get(twitch_url) as response:
                data = await response.json()

        fmt = "Username: {}".format(data['display_name'])
        fmt += "\nStatus: {}".format(data['status'])
        fmt += "\nFollowers: {}".format(data['followers'])
        fmt += "\nURL: {}".format(url)
        await self.bot.say("```\n{}```".format(fmt))

    @twitch.command(name='add', pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL

        EXAMPLE: !twitch add MyTwitchName
        RESULT: Saves your twitch URL; notifications will be sent to this server when you go live"""
        # This uses a lookbehind to check if twitch.tv exists in the url given
        # If it does, it matches twitch.tv/user and sets the url as that
        # Then (in the else) add https://www. to that
        # Otherwise if it doesn't match, we'll hit an AttributeError due to .group(0)
        # This means that the url was just given as a user (or something complete invalid)
        # So set URL as https://www.twitch.tv/[url]
        # Even if this was invalid such as https://www.twitch.tv/google.com/
        # For example, our next check handles that
        try:
            url = re.search("((?<=://)?twitch.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.twitch.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)

        # Try to find the channel provided, we'll get a 404 response if it does not exist
        with aiohttp.ClientSession() as s:
            async with s.get(url) as response:
                if not response.status == 200:
                    await self.bot.say("That twitch user does not exist! "
                                       "What would be the point of adding a nonexistant twitch user? Silly")
                    return

        r_filter = {'member_id': ctx.message.author.id}
        entry = {'twitch_url': url,
                 'servers': [ctx.message.server.id],
                 'notifications_on': 1,
                 'live': 0,
                 'member_id': ctx.message.author.id}
        update = {'twitch_url': url}

        # Check to see if this user has already saved a twitch URL
        # If they have, update the URL, otherwise create a new entry
        # Assuming they're not live, and notifications should be on
        if not await config.add_content('twitch', entry, r_filter):
            await config.update_content('twitch', update, r_filter)
        await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))

    @twitch.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL

        EXAMPLE: !twitch remove
        RESULT: I stop saving your twitch URL"""
        # Just try to remove it, if it doesn't exist, nothing is going to happen
        r_filter = {'member_id': ctx.message.author.id}
        await config.remove_content('twitch', r_filter)
        await self.bot.say("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))

    @twitch.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to modify notification settings for your twitch user
        Call this command by itself to add 'this' server as one that will be notified when you on/offline

        EXAMPLE: !twitch notify
        RESULT: This server will now be notified when you go live"""
        r_filter = {'member_id': ctx.message.author.id}
        result = await config.get_content('twitch', r_filter)
        # Check if this user is saved at all
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        # Then check if this server is already added as one to notify in
        elif ctx.message.server.id in result[0]['servers']:
            await self.bot.say("I am already set to notify in this server...")
        else:
            await config.update_content('twitch', {'servers': r.row['servers'].append(ctx.message.server.id)}, r_filter)

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns twitch notifications on

        EXAMPLE: !twitch notify on
        RESULT: Notifications will be sent when you go live"""
        r_filter = {'member_id': ctx.message.author.id}
        if await config.update_content('twitch', {"notifications_on": 1}, r_filter):
            await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))
        else:
            await self.bot.say("I can't notify if you go live if I don't know your twitch URL yet!")

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns twitch notifications off

        EXAMPLE: !twitch notify off
        RESULT: Notifications will not be sent when you go live"""
        r_filter = {'member_id': ctx.message.author.id}
        if await config.update_content('twitch', {"notifications_on": 1}, r_filter):
            await self.bot.say(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))
        else:
            await self.bot.say(
                "I mean, I'm already not going to notify anyone, because I don't have your twitch URL saved...")


def setup(bot):
    t = Twitch(bot)
    bot.loop.create_task(t.check_channels())
    bot.add_cog(Twitch(bot))
