from discord.ext import commands
from .utils import config
from .utils.config import getPhrase
from .utils import checks
import aiohttp
import asyncio
import discord
import json
import re


async def channel_online(channel: str):
    url = "https://api.twitch.tv/kraken/streams/{}".format(channel)
    with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            response = await r.text()
    try:
        data = json.loads(response)
        return data['stream'] is not None
    except KeyError:
        return False
    except json.JSONDecodeError:
        return False


class Twitch:
    """Class for some twitch integration
    You can add or remove your twitch stream for your user
    I will then notify the server when you have gone live or offline"""

    def __init__(self, bot):
        self.bot = bot

    async def checkChannels(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed:
            twitch = config.getContent('twitch')
            for m_id, r in twitch.items():
                url = r['twitch_url']
                live = r['live']
                notify = r['notifications_on']
                user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
                online = await channel_online(user)
                if not live and notify and online:
                    server = discord.utils.find(lambda s: s.id == r['server_id'], self.bot.servers)
                    member = discord.utils.find(lambda m: m.id == m_id, server.members)
                    twitch[m_id]['live'] = 1
                    fmt = getPhrase("LIVESTREAM:USER_ONLINE").format(member.mention, url)
                    await self.bot.send_message(server, fmt)
                    config.saveContent('twitch', twitch)
                elif live and not online:
                    server = discord.utils.find(lambda s: s.id == r['server_id'], self.bot.servers)
                    member = discord.utils.find(lambda m: m.id == m_id, server.members)
                    twitch[m_id]['live'] = 0
                    fmt = getPhrase("LIVESTREAM:USER_OFFLINE").format(member.mention, url)
                    await self.bot.send_message(server, fmt)
                    config.saveContent('twitch', twitch)
            await asyncio.sleep(30)

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    @checks.customPermsOrRole(send_messages=True)
    async def twitch(self, ctx, *, member: discord.Member=None):
        """Use this command to check the twitch info of a user"""
        if member is None:
            member = ctx.message.author

        twitch_channels = config.getContent('twitch') or {}
        result = twitch_channels.get(ctx.message.author.id)
        if result is None:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_NO_URL").format(ctx.message.author.mention, config.commandPrefix, getPhrase("LIVESTREAM:TWITCH")))
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
    @checks.customPermsOrRole(send_messages=True)
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL"""
        try:
            url = re.search("((?<=://)?twitch.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.twitch.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)

        with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if not r.status == 200:
                    await self.bot.say(getPhrase("LIVESTREAM:ERROR_INVALID_STREAM_NAME").format(getPhrase("LIVESTREAM:TWITCH")))
                    return

        twitch = config.getContent('twitch') or {}
        result = twitch.get(ctx.message.author.id)

        if result is not None:
            twitch[ctx.message.author.id]['twitch_url'] = url
            channel = picarto_urls[ctx.message.author.id]['servers']
        else:
            channel = discord.utils.get(ctx.message.server.channels, name='livestream_announcements', type=discord.ChannelType.text).id or discord.utils.get(ctx.message.server.channels, name='announcements', type=discord.ChannelType.text).id
            ac = True
            if not channel:
                channel = ctx.message.channel.id
                ac = True
            twitch[ctx.message.author.id] = {'twitch_url': url, 'server_id': ctx.message.server.id,
                                             'notifications_on': 1, 'live': 0}
        config.saveContent('twitch', twitch)
        await self.bot.say(getPhrase("LIVESTREAM:URL_SAVED").format(getPhrase("LIVESTREAM:TWITCH"), ctx.message.author.mention, getPhrase("LIVESTREAM:DEDICATED_ANNOUNCEMENT") if ac else getPhrase("THIS")))

    @twitch.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL"""
        twitch = config.getContent('twitch')
        if twitch.get(ctx.message.author.id) is not None:
            del twitch[ctx.message.author.id]
            config.saveContent('twitch', twitch)
            await self.bot.say(getPhrase("LIVESTREAM:URL_REMOVED").format(getPhrase("LIVESTREAM:TWITCH"), ctx.message.author.mention))
        else:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_NO_URL").format(ctx.message.author.mention, config.commandPrefix, getPhrase("LIVESTREAM:TWITCH")))

    @twitch.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify(self, ctx, channel: discord.Channel = None):
        """This can be used to turn twitch notifications on or off
        Call this command by itself, with a channel name, to change which one has the notification sent to it"""
        channel = channel or ctx.message.channel
        member = ctx.message.author

        twitch = config.getContent('twitch') or {}
        result = twitch.get(member.id)
        if result is None:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_NO_URL").format(ctx.message.author.mention, config.commandPrefix, getPhrase("LIVESTREAM:TWITCH")))
        else:
            twitch[member.id]['channel_id'] = channel.id
            config.saveContent('twitch', twitch)
            await self.bot.say(getPhrase("LIVESTREAM:NOTIFICATION_CHANNEL_CHANGED").format(channel.name))

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify_on(self, ctx):
        """Turns twitch notifications on"""
        twitch = config.getContent('twitch')
        result = twitch.get(ctx.message.author.id)
        if result is None:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_NO_URL").format(ctx.message.author.mention, config.commandPrefix, getPhrase("LIVESTREAM:TWITCH")))
        elif result['notifications_on']:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_ALREADY_NOTIFYING").format(ctx.message.author.mention))
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 1
            config.saveContent('twitch', twitch)
            await self.bot.say(getPhrase("LIVESTREAM:NOTIFICATIONS_ON").format(ctx.message.author.mention))

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify_off(self, ctx):
        """Turns twitch notifications off"""
        twitch = config.getContent('twitch')
        if twitch.get(ctx.message.author.id) is None:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_NO_URL").format(ctx.message.author.mention, config.commandPrefix, getPhrase("LIVESTREAM:TWITCH")))
        elif not twitch.get(ctx.message.author.id)['notifications_on']:
            await self.bot.say(getPhrase("LIVESTREAM:ERROR_ALREADY_NOT_NOTIFYING").format(ctx.message.author.mention))
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 0
            if config.saveContent('twitch', twitch):
                await self.bot.say(getPhrase("LIVESTREAM:NOTIFICATIONS_OFF").format(ctx.message.author.mention))
            else:
                await self.bot.say(getPhrase("ERROR_UNABLE_TO_SAVE"))


def setup(bot):
    t = Twitch(bot)
    config.loop.create_task(t.checkChannels())
    bot.add_cog(Twitch(bot))
