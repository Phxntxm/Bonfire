import aiohttp
import json
import asyncio
import discord
import re

from discord.ext import commands
from .utils import config
from .utils import checks

base_url = 'https://ptvappapi.picarto.tv'

# This is a public key for use, I don't care if this is seen
key = '03e26294-b793-11e5-9a41-005056984bd4'


async def check_online(stream):
    try:
        url = '{}/channel/{}?key={}'.format(base_url, stream, key)
        with aiohttp.ClientSession(headers={"User-Agent": "Bonfire/1.0.0"}) as s:
            async with s.get(url) as r:
                response = await r.text()
        return json.loads(response).get('is_online')
    except:
        return False


class Picarto:
    def __init__(self, bot):
        self.bot = bot

    async def check_channels(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed:
            picarto = config.getContent('picarto') or {}
            for m_id, r in picarto.items():
                url = r['picarto_url']
                live = r['live']
                notify = r['notifications_on']
                user = re.search("(?<=picarto.tv/)(.*)", url).group(1)
                online = await check_online(user)

                if not live and notify and online:
                    for server_id, channel_id in r['servers'].items():
                        server = self.bot.get_server(server_id)
                        channel = self.bot.get_channel(channel_id)
                        member = discord.utils.find(lambda m: m.id == m_id, server.members)

                        picarto[m_id]['live'] = 1
                        fmt = "{} has just gone live! View their stream at {}".format(member.display_name, url)
                        config.saveContent('picarto', picarto)
                        await self.bot.send_message(channel, fmt)
                elif live and not online:
                    for server_id, channel_id in r['servers'].items():
                        server = self.bot.get_server(server_id)
                        channel = self.bot.get_channel(channel_id)
                        member = discord.utils.find(lambda m: m.id == m_id, server.members)

                        picarto[m_id]['live'] = 0
                        fmt = "{} has just gone offline! Catch them next time they stream at {}".format(
                            member.display_name,
                            url)
                        config.saveContent('picarto', picarto)
                        await self.bot.send_message(channel, fmt)
            await asyncio.sleep(30)

    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.customPermsOrRole(send_messages=True)
    async def picarto(self, ctx, member: discord.Member = None):
        """This command can be used to view Picarto stats about a certain member"""
        member = member or ctx.message.author
        picarto_urls = config.getContent('picarto') or {}
        member_url = picarto_urls.get(member.id)
        if not member_url:
            await self.bot.say("That user does not have a picarto url setup!")
            return
        member_url = member_url['picarto_url']

        stream = re.search("(?<=picarto.tv/)(.*)", member_url).group(1)
        url = '{}/channel/{}?key={}'.format(base_url, stream, key)
        with aiohttp.ClientSession(headers={"User-Agent": "Bonfire/1.0.0"}) as s:
            async with s.get(url) as r:
                response = await r.text()

        data = json.loads(response)
        things_to_print = ['channel', 'commissions_enabled', 'is_nsfw', 'program', 'tablet', 'followers',
                           'content_type']
        fmt = "\n".join(
            "{}: {}".format(i.title().replace("_", " "), r) for i, r in data.items() if i in things_to_print)
        social_links = data.get('social_urls')
        if social_links:
            fmt2 = "\n".join("\t{}: {}".format(i.title().replace("_", " "), r) for i, r in social_links.items())
            fmt = "{}\nSocial Links:\n{}".format(fmt, fmt2)
        await self.bot.say("Picarto stats for {}: ```\n{}```".format(member.display_name, fmt))

    @picarto.command(name='add', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def add_picarto_url(self, ctx, url: str):
        """Saves your user's picarto URL"""
        try:
            url = re.search("((?<=://)?picarto.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.picarto.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)

        api_url = '{}/channel/{}?key={}'.format(base_url, re.search("https://www.picarto.tv/(.*)", url).group(1), key)

        with aiohttp.ClientSession() as s:
            async with s.get(api_url) as r:
                if not r.status == 200:
                    await self.bot.say("That Picarto user does not exist! "
                                       "What would be the point of adding a nonexistant Picarto user? Silly")
                    return

        picarto_urls = config.getContent('picarto') or {}
        result = picarto_urls.get(ctx.message.author.id)

        if result is not None:
            picarto_urls[ctx.message.author.id]['picarto_url'] = url
        else:
            picarto_urls[ctx.message.author.id] = {'picarto_url': url,
                                                   'servers': {ctx.message.server.id: discord.utils.get(ctx.message.server.channels, name='livestream_announcements', type=discord.ChannelType.text) or ctx.message.channel.id},
                                                   'notifications_on': 1, 'live': 0}
        config.saveContent('picarto', picarto_urls)
        await self.bot.say(
            "I have just saved your Picarto url {}, this channel will now send a notification when you go live".format(
                ctx.message.author.mention))

    @picarto.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def remove_picarto_url(self, ctx):
        """Removes your picarto URL"""
        picarto = config.getContent('picarto') or {}
        if picarto.get(ctx.message.author.id) is not None:
            del picarto[ctx.message.author.id]
            config.saveContent('picarto', picarto)
            await self.bot.say("I am no longer saving your picarto URL {}".format(ctx.message.author.mention))
        else:
            await self.bot.say(
                "I do not have your picarto URL added {}. You can save your picarto url with !picarto add".format(
                    ctx.message.author.mention))

    @picarto.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify(self, ctx, channel: discord.Channel = None):
        """This can be used to turn picarto notifications on or off
        Call this command by itself, with a channel name, to change which one has the notification sent to it"""
        channel = channel or ctx.message.channel
        member = ctx.message.author

        picarto = config.getContent('picarto') or {}
        result = picarto.get(member.id)
        if result is None:
            await self.bot.say(
                "I do not have your picarto URL added {}. You can save your picarto url with !picarto add".format(
                    member.mention))

        picarto[member.id]['servers'][ctx.message.server.id] = channel.id
        config.saveContent('picarto', picarto)
        await self.bot.say(
            "I have just changed which channel will be notified when you go live, to `{}`".format(channel.name))

    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify_on(self, ctx):
        """Turns picarto notifications on"""
        picarto = config.getContent('picarto') or {}
        result = picarto.get(ctx.message.author.id)
        if result is None:
            await self.bot.say(
                "I do not have your picarto URL added {}. You can save your picarto url with !picarto add".format(
                    ctx.message.author.mention))
        elif result['notifications_on']:
            await self.bot.say("What do you want me to do, send two notifications? Not gonna happen {}".format(
                ctx.message.author.mention))
        else:
            picarto[ctx.message.author.id]['notifications_on'] = 1
            config.saveContent('picarto', picarto)
            await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def notify_off(self, ctx):
        """Turns picarto notifications off"""
        picarto = config.getContent('picarto') or {}
        if picarto.get(ctx.message.author.id) is None:
            await self.bot.say(
                "I do not have your picarto URL added {}. You can save your picarto url with !picarto add".format(
                    ctx.message.author.mention))
        elif not picarto.get(ctx.message.author.id)['notifications_on']:
            await self.bot.say("I am already set to not notify if you go live! Pay attention brah {}".format(
                ctx.message.author.mention))
        else:
            picarto[ctx.message.author.id]['notifications_on'] = 0
            config.saveContent('picarto', picarto)
            await self.bot.say(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))


def setup(bot):
    p = Picarto(bot)
    config.loop.create_task(p.check_channels())
    bot.add_cog(Picarto(bot))