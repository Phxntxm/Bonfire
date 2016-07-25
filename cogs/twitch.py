from discord.ext import commands
from .utils import config
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
    data = json.loads(response)
    return data['stream'] is not None


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
                if not live and notify and await channel_online(user):
                    server = discord.utils.find(lambda s: s.id == r['server_id'], self.bot.servers)
                    member = discord.utils.find(lambda m: m.id == m_id, server.members)
                    twitch[m_id]['live'] = 1
                    fmt = "{} has just gone live! View their stream at {}".format(member.name, url)
                    await self.bot.send_message(server, fmt)
                    config.saveContent('twitch',twitch)
                elif live and not await channel_online(user):
                    server = discord.utils.find(lambda s: s.id == r['server_id'], self.bot.servers)
                    member = discord.utils.find(lambda m: m.id == m_id, server.members)
                    twitch[m_id]['live'] = 0
                    fmt = "{} has just gone offline! Catch them next time they stream at {}".format(member.name, url)
                    await self.bot.send_message(server,fmt)
                    config.saveContent('twitch',twitch)
            await asyncio.sleep(30)

    @commands.group(no_pm=True, invoke_without_command=True, pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def twitch(self, ctx, *, member: discord.Member=None):
        """Use this command to check the twitch info of a user"""
        if member is None:
            member = ctx.message.author
            
        result = config.getContent('twitch').get(ctx.message.author.id)
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
        await self.bot.say("```{}```".format(fmt))

    @twitch.command(name='add', pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
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
                    await self.bot.say("That twitch user does not exist! "
                                       "What would be the point of adding a nonexistant twitch user? Silly")
                    return

        twitch = config.getContent('twitch')
        result = twitch.get(ctx.message.author.id)

        if result is not None:
            twitch[ctx.message.author.id]['twitch_url'] = url
        else:
            twitch[ctx.message.author.id] = {'twitch_url': url, 'server_id': ctx.message.server.id,
                                             'notifications_on': 1, 'live': 0}
        if config.saveContent('twitch', twitch):
            await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))
        else:
            await self.bot.say("I was unable to save this data")

    @twitch.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL"""
        twitch = config.getContent('twitch')
        if twitch.get(ctx.message.author.id) is not None:
            del twitch[ctx.message.author.id]
            if config.saveContent('twitch', twitch):
                await self.bot.say("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))
            else:
                await self.bot.say("I was unable to save this data")
        else:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))

    @twitch.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.customPermsOrRole("send_messages")
    async def notify(self, ctx):
        """This can be used to turn notifications on or off"""
        pass

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def notify_on(self, ctx):
        """Turns twitch notifications on"""
        twitch = config.getContent('twitch')
        result = twitch.get(ctx.message.author.id)
        if result is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        elif result['notifications_on']:
            await self.bot.say("What do you want me to do, send two notifications? Not gonna happen {}".format(
                ctx.message.author.mention))
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 1
            if config.saveContent('twitch', twitch):
                await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                    ctx.message.author.mention))
            else:
                await self.bot.say("I was unable to save this data")

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def notify_off(self, ctx):
        """Turns twitch notifications off"""
        twitch = config.getContent('twitch')
        if twitch.get(ctx.message.author.id) is None:
            await self.bot.say(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        elif not twitch.get(ctx.message.author.id)['notifications_on']:
            await self.bot.say("I am already set to not notify if you go live! Pay attention brah {}".format(
                ctx.message.author.mention))
        else:
            twitch[ctx.message.author.id]['notifications_on'] = 0
            if config.saveContent('twitch', twitch):
                await self.bot.say(
                    "I will not notify if you go live anymore {}, "
                    "are you going to stream some lewd stuff you don't want people to see?~".format(
                        ctx.message.author.mention))
            else:
                await self.bot.say("I was unable to save this data")


def setup(bot):
    t = Twitch(bot)
    config.loop.create_task(t.checkChannels())
    bot.add_cog(Twitch(bot))
