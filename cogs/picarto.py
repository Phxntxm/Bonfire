import aiohttp
import asyncio
import discord
import re
import rethinkdb as r
import traceback
import logging

from discord.ext import commands

from . import utils

log = logging.getLogger()
BASE_URL = 'https://ptvappapi.picarto.tv'

# This is a public key for use, I don't care if this is seen
api_key = '03e26294-b793-11e5-9a41-005056984bd4'


class Picarto:
    def __init__(self, bot):
        self.bot = bot

    async def get_online_users(self):
        # This method is in place to just return all online users so we can compare against it
        url = BASE_URL + '/online/all'
        payload = {'key': api_key}
        self.online_channels = await utils.request(url, payload=payload)

    def channel_online(self, channel):
        # Channel is the name we are checking against that
        # This creates a list of all users that match this channel name (should only ever be 1)
        # And returns True as long as it is more than 0
        channel = re.search("(?<=picarto.tv/)(.*)", channel).group(1)
        matches = [stream for stream in self.online_channels if stream['channel_name'].lower() == channel.lower()]
        return len(matches) > 0

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # This is a loop that runs every 30 seconds, checking if anyone has gone online
        try:
            while not self.bot.is_closed:
                await self.get_online_users()
                picarto = await utils.filter_content('picarto', {'notifications_on': 1})
                for data in picarto:
                    m_id = data['member_id']
                    url = data['picarto_url']
                    # Check if they are online
                    online = self.channel_online(url)
                    # If they're currently online, but saved as not then we'll send our notification
                    if online and data['live'] == 0:
                        for s_id in data['servers']:
                            server = self.bot.get_server(s_id)
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            server_settings = await utils.get_content('server_settings', s_id)
                            if server_settings is not None:
                                channel_id = server_settings.get('notification_channel', s_id)
                            else:
                                channel_id = s_id
                            channel = server.get_channel(channel_id)
                            await self.bot.send_message(channel, "{} has just gone live! View their stream at <{}>".format(member.display_name, data['picarto_url']))
                            self.bot.loop.create_task(utils.update_content('picarto', {'live': 1}, m_id))
                    elif not online and data['live'] == 1:
                        for s_id in data['servers']:
                            server = self.bot.get_server(s_id)
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            server_settings = await utils.get_content('server_settings', s_id)
                            if server_settings is not None:
                                channel_id = server_settings.get('notification_channel', s_id)
                            else:
                                channel_id = s_id
                            channel = server.get_channel(channel_id)
                            await self.bot.send_message(channel, "{} has just gone offline! View their stream next time at <{}>".format(member.display_name, data['picarto_url']))
                            self.bot.loop.create_task(utils.update_content('picarto', {'live': 0}, m_id))
                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(invoke_without_command=True, no_pm=True, pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def picarto(self, ctx, member: discord.Member = None):
        """This command can be used to view Picarto stats about a certain member

        EXAMPLE: !picarto @otherPerson
        RESULT: Info about their picarto stream"""

        # If member is not given, base information on the author
        member = member or ctx.message.author
        picarto_entry = await utils.get_content('picarto', member.id)
        if picarto_entry is None:
            await self.bot.say("That user does not have a picarto url setup!")
            return

        member_url = picarto_entry['picarto_url']

        # Use regex to get the actual username so that we can make a request to the API
        stream = re.search("(?<=picarto.tv/)(.*)", member_url).group(1)
        url = BASE_URL + '/channel/{}'.format(stream)
        payload = {'key': api_key}

        data = await utils.request(url, payload=payload)
        if data is None:
            await self.bot.say("I couldn't connect to Picarto!")
            return

        # Not everyone has all these settings, so use this as a way to print information if it does, otherwise ignore it
        things_to_print = ['channel', 'commissions_enabled', 'is_nsfw', 'program', 'tablet', 'followers',
                           'content_type']

        embed = discord.Embed(title='{}\'s Picarto'.format(data['channel']), url=url)
        if data['avatar_url']:
            embed.set_thumbnail(url=data['avatar_url'])

        for i, result in data.items():
            if i in things_to_print and str(result):
                i = i.title().replace('_', ' ')
                embed.add_field(name=i, value=str(result))

        # Social URL's can be given if a user wants them to show
        # Print them if they exist, otherwise don't try to include them
        for i, result in data['social_urls'].items():
            embed.add_field(name=i.title(), value=result)

        await self.bot.say(embed=embed)

    @picarto.command(name='add', no_pm=True, pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def add_picarto_url(self, ctx, url: str):
        """Saves your user's picarto URL

        EXAMPLE: !picarto add MyUsername
        RESULT: Your picarto stream is saved, and notifications should go to this server"""

        # This uses a lookbehind to check if picarto.tv exists in the url given
        # If it does, it matches picarto.tv/user and sets the url as that
        # Then (in the else) add https://www. to that
        # Otherwise if it doesn't match, we'll hit an AttributeError due to .group(0)
        # This means that the url was just given as a user (or something complete invalid)
        # So set URL as https://www.picarto.tv/[url]
        # Even if this was invalid such as https://www.picarto.tv/picarto.tv/user
        # For example, our next check handles that
        try:
            url = re.search("((?<=://)?picarto.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.picarto.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)
        channel = re.search("https://www.picarto.tv/(.*)", url).group(1)
        api_url = BASE_URL + '/channel/{}'.format(channel)
        payload = {'key': api_key}

        data = await utils.request(api_url, payload=payload)
        if not data:
            await self.bot.say("That Picarto user does not exist! What would be the point of adding a nonexistant "
                               "Picarto user? Silly")
            return

        key = ctx.message.author.id
        entry = {'picarto_url': url,
                 'servers': [ctx.message.server.id],
                 'notifications_on': 1,
                 'live': 0,
                 'member_id': key}
        if await utils.add_content('picarto', entry):
            await self.bot.say(
                "I have just saved your Picarto URL {}, this server will now be notified when you go live".format(
                    ctx.message.author.mention))
        else:
            await utils.update_content('picarto', {'picarto_url': url}, key)
            await self.bot.say("I have just updated your Picarto URL")

    @picarto.command(name='remove', aliases=['delete'], no_pm=True, pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def remove_picarto_url(self, ctx):
        """Removes your picarto URL"""
        if await utils.remove_content('picarto', ctx.message.author.id):
            await self.bot.say("I am no longer saving your picarto URL {}".format(ctx.message.author.mention))
        else:
            await self.bot.say(
                "I do not have your picarto URL added {}. You can save your picarto url with {}picarto add".format(
                    ctx.message.author.mention, ctx.prefix))

    @picarto.group(no_pm=True, invoke_without_command=True, pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to turn picarto notifications on or off
        Call this command by itself, to add this server to the list of servers to be notified

        EXAMPLE: !picarto notify
        RESULT: This server will now be notified of you going live"""
        key = ctx.message.author.id
        result = await utils.get_content('picarto', key)
        # Check if this user is saved at all
        if result is None:
            await self.bot.say(
                "I do not have your Picarto URL added {}. You can save your Picarto url with !picarto add".format(
                    ctx.message.author.mention))
        # Then check if this server is already added as one to notify in
        elif ctx.message.server.id in result['servers']:
            await self.bot.say("I am already set to notify in this server...")
        else:
            await utils.update_content('picarto', {'servers': r.row['servers'].append(ctx.message.server.id)}, key)

    @notify.command(name='on', aliases=['start,yes'], no_pm=True, pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns picarto notifications on

        EXAMPLE: !picarto notify on
        RESULT: Notifications are sent when you go live"""
        await utils.update_content('picarto', {'notifications_on': 1}, ctx.message.author.id)
        await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
            ctx.message.author.mention))

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns picarto notifications off

        EXAMPLE: !picarto notify off
        RESULT: No more notifications sent when you go live"""
        await utils.update_content('picarto', {'notifications_on': 0}, ctx.message.author.id)
        await self.bot.say(
            "I will not notify if you go live anymore {}, "
            "are you going to stream some lewd stuff you don't want people to see?~".format(
                ctx.message.author.mention))


def setup(bot):
    p = Picarto(bot)
    bot.loop.create_task(p.check_channels())
    bot.add_cog(Picarto(bot))