from discord.ext import commands
from .utils import config
from .utils import checks
import aiohttp
import asyncio
import discord
import json
import re


async def channel_online(channel: str):
    # Check a specific channel's data, and get the response in text format
    url = "https://api.twitch.tv/kraken/streams/{}".format(channel)
    with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            response = await r.text()

    # For some reason Twitch's API call is not reliable, sometimes it returns stream as None
    # That is what we're checking specifically, sometimes it doesn't exist in the returned JSON at all
    # Sometimes it returns something that cannot be decoded with JSON
    # In either error case, just assume they're offline, the next check will most likely work
    try:
        data = json.loads(response)
        return data['stream'] is not None
    except (KeyError, json.JSONDecodeError):
        return False


class Twitch:
    """Class for some twitch integration
    You can add or remove your twitch stream for your user
    I will then notify the server when you have gone live or offline"""

    def __init__(self, bot):
        self.bot = bot

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # Loop through as long as the bot is connected
        while not self.bot.is_closed:
            twitch = await config.get_content('twitch')
            # Online/offline is based on whether they are set to such, in the config file
            # This means they were detected as online/offline before and we check for a change
            online_users = {m_id: data for m_id, data in twitch.items() if data['notifications_on'] and data['live']}
            offline_users = {m_id: data for m_id, data in twitch.items() if
                             data['notifications_on'] and not data['live']}
            for m_id, r in offline_users.items():
                # Get their url and their user based on that url
                url = r['twitch_url']
                user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                # Check if they are online right now
                if await channel_online(user):
                    for server_id in r['servers']:
                        # Get the channel to send the message to, based on the saved alert's channel
                        server = self.bot.get_server(server_id)
                        server_alerts = await config.get_content('server_alerts')
                        channel_id = server_alerts.get(server_id) or server_id
                        channel = self.bot.get_channel(channel_id)
                        # Get the member that has just gone live
                        member = discord.utils.get(server.members, id=m_id)

                        fmt = "{} has just gone live! View their stream at {}".format(member.display_name, url)
                        await self.bot.send_message(channel, fmt)
                    twitch[m_id]['live'] = 1
                    await config.save_content('twitch', twitch)
            for m_id, r in online_users.items():
                # Get their url and their user based on that url
                url = r['twitch_url']
                user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                # Check if they are online right now
                if not await channel_online(user):
                    for server_id in r['servers']:
                        # Get the channel to send the message to, based on the saved alert's channel
                        server = self.bot.get_server(server_id)
                        server_alerts = await config.get_content('server_alerts')
                        channel_id = server_alerts.get(server_id) or server_id
                        channel = self.bot.get_channel(channel_id)
                        # Get the member that has just gone live
                        member = discord.utils.get(server.members, id=m_id)
                        fmt = "{} has just gone offline! Catch them next time they stream at {}".format(
                            member.display_name, url)
                        await self.bot.send_message(channel, fmt)
                    twitch[m_id]['live'] = 0
                    await config.save_content('twitch', twitch)
            await asyncio.sleep(30)

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def twitch(self, ctx, *, member: discord.Member = None):
        """Use this command to check the twitch info of a user"""
        if member is None:
            member = ctx.message.author

        twitch_channels = await config.get_content('twitch')
        result = twitch_channels.get(ctx.message.author.id)
        if result is None:
            await self.bot.say("{} has not saved their twitch URL yet!".format(member.name))
            return

        url = result['twitch_url']
        user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
        with aiohttp.ClientSession() as s:
            async with s.get("https://api.twitch.tv/kraken/channels/{}".format(user)) as r:
                response = await r.text()
        data = json.loads(response)

        fmt = "Username: {}".format(data['display_name'])
        fmt += "\nStatus: {}".format(data['status'])
        fmt += "\nFollowers: {}".format(data['followers'])
        fmt += "\nURL: {}".format(url)
        await self.bot.say("```\n{}```".format(fmt))

    @twitch.command(name='add', pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL"""
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
            async with s.get(url) as r:
                if not r.status == 200:
                    await self.bot.say("That twitch user does not exist! "
                                       "What would be the point of adding a nonexistant twitch user? Silly")
                    return

        twitch = await config.get_content('twitch')
        result = twitch.get(ctx.message.author.id)

        # Check to see if this user has already saved a twitch URL
        # If they have, update the URL, otherwise create a new entry
        # Assuming they're not live, and notifications should be on
        if result is not None:
            twitch[ctx.message.author.id]['twitch_url'] = url
        else:
            twitch[ctx.message.author.id] = {'twitch_url': url, 'servers': [ctx.message.server.id],
                                             'notifications_on': 1, 'live': 0}
        await config.save_content('twitch', twitch)
        await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))

    @twitch.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL"""
        twitch = await config.get_content('twitch')
        # Make sure the user exists before trying to delete them from the list
        if twitch.get(ctx.message.author.id) is not None:
            # Simply remove this user from the list, and save
            del twitch[ctx.message.author.id]
            await config.save_content('twitch', twitch)
            await self.bot.say("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))
        else:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))

    @twitch.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to modify notification settings for your twitch user
        Call this command by itself to add 'this' server as one that will be notified when you on/offline"""
        twitch = await config.get_content('twitch')
        result = twitch.get(ctx.message.author.id)
        # Check if this user is saved at all
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        # Otherwise we just need to append the server's ID to the servers list
        else:
            twitch[ctx.message.author.id]['servers'].append(ctx.message.server.id)
            await config.save_content('twitch', twitch)

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns twitch notifications on"""
        # Make sure this user is saved before we attempt to modify their information
        twitch = await config.get_content('twitch')
        result = twitch.get(ctx.message.author.id)
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        # Then check to see if notifications are already on
        elif result['notifications_on']:
            await self.bot.say("What do you want me to do, send two notifications? Not gonna happen {}".format(
                ctx.message.author.mention))
        # Otherwise, turn on notifications
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 1
            await config.save_content('twitch', twitch)
            await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns twitch notifications off"""
        # This method is exactly the same, except for turning off notifcations instead of on
        twitch = await config.get_content('twitch')
        if twitch.get(ctx.message.author.id) is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        elif not twitch.get(ctx.message.author.id)['notifications_on']:
            await self.bot.say("I am already set to not notify if you go live! Pay attention brah {}".format(
                ctx.message.author.mention))
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 0
            await self.bot.say(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))


def setup(bot):
    t = Twitch(bot)
    config.loop.create_task(t.check_channels())
    bot.add_cog(Twitch(bot))
