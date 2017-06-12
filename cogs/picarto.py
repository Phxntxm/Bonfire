import asyncio
import discord
import re
import traceback
import logging

from discord.ext import commands

from . import utils

log = logging.getLogger()
BASE_URL = 'https://api.picarto.tv/v1'


class Picarto:
    def __init__(self, bot):
        self.bot = bot

    # noinspection PyAttributeOutsideInit
    async def get_online_users(self):
        # This method is in place to just return all online users so we can compare against it
        url = BASE_URL + '/online'
        payload = {
            'adult': True,
            'gaming': True
        }
        self.online_channels = await utils.request(url, payload=payload)

    def channel_online(self, channel):
        # Channel is the name we are checking against that
        # This creates a list of all users that match this channel name (should only ever be 1)
        # And returns True as long as it is more than 0
        if not self.online_channels:
            return False
        channel = re.search("(?<=picarto.tv/)(.*)", channel).group(1)
        return channel in [stream['name'].lower() for stream in self.online_channels]

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # This is a loop that runs every 30 seconds, checking if anyone has gone online
        try:
            while not self.bot.is_closed():
                await self.get_online_users()
                picarto = self.bot.db.load('picarto', table_filter={'notifications_on': 1})
                for data in picarto:
                    m_id = int(data['member_id'])
                    url = data['picarto_url']
                    # Check if they are online
                    online = self.channel_online(url)
                    # If they're currently online, but saved as not then we'll send our notification
                    if online and data['live'] == 0:
                        for s_id in data['servers']:
                            server = self.bot.get_guild(int(s_id))
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            channel_id = self.bot.db.load('server_settings', key=s_id,
                                                          pluck='notifications_channel') or int(s_id)
                            channel = server.get_channel(channel_id)
                            try:
                                await channel.send(
                                    "{} has just gone live! View their stream at <{}>".format(member.display_name,
                                                                                              data['picarto_url']))
                            except discord.Forbidden:
                                pass
                            self.bot.db.save('picarto', {'live': 1, 'member_id': str(m_id)})
                    elif not online and data['live'] == 1:
                        for s_id in data['servers']:
                            server = self.bot.get_guild(int(s_id))
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            channel_id = self.bot.db.load('server_settings', key=s_id,
                                                          pluck='notifications_channel') or int(s_id)
                            channel = server.get_channel(channel_id)
                            try:
                                await channel.send(
                                    "{} has just gone offline! View their stream next time at <{}>".format(
                                        member.display_name, data['picarto_url']))
                            except discord.Forbidden:
                                pass
                            self.bot.db.save('picarto', {'live': 0, 'member_id': str(m_id)})
                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def picarto(self, ctx, member: discord.Member = None):
        """This command can be used to view Picarto stats about a certain member

        EXAMPLE: !picarto @otherPerson
        RESULT: Info about their picarto stream"""
        await ctx.message.channel.trigger_typing()

        # If member is not given, base information on the author
        member = member or ctx.message.author
        member_url = self.bot.db.load('picarto', key=member.id, pluck='picarto_url')
        if member_url is None:
            await ctx.send("That user does not have a picarto url setup!")
            return

        # Use regex to get the actual username so that we can make a request to the API
        stream = re.search("(?<=picarto.tv/)(.*)", member_url).group(1)
        url = BASE_URL + '/channel/name/{}'.format(stream)

        data = await utils.request(url)
        if data is None:
            await ctx.send("I couldn't connect to Picarto!")
            return

        # Not everyone has all these settings, so use this as a way to print information if it does, otherwise ignore it
        things_to_print = ['comissions', 'adult', 'followers', 'category', 'online']

        embed = discord.Embed(title='{}\'s Picarto'.format(data['name']), url=member_url)
        if data.get('avatar_url'):
            embed.set_thumbnail(url=data['avatar_url'])

        for i, result in data.items():
            if i in things_to_print and str(result):
                i = i.title().replace('_', ' ')
                embed.add_field(name=i, value=str(result))

        # Social URL's can be given if a user wants them to show
        # Print them if they exist, otherwise don't try to include them
        social_links = data.get('social_urls', {})

        for i, result in social_links.items():
            embed.add_field(name=i.title(), value=result)

        await ctx.send(embed=embed)

    @picarto.command(name='add')
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def add_picarto_url(self, ctx, url: str):
        """Saves your user's picarto URL

        EXAMPLE: !picarto add MyUsername
        RESULT: Your picarto stream is saved, and notifications should go to this guild"""
        await ctx.message.channel.trigger_typing()

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
        api_url = BASE_URL + '/channel/name/{}'.format(channel)

        data = await utils.request(api_url)
        if not data:
            await ctx.send("That Picarto user does not exist! What would be the point of adding a nonexistant Picarto "
                           "user? Silly")
            return

        key = str(ctx.message.author.id)

        # Check if it exists first, if it does we don't want to override some of the settings
        result = self.bot.db.load('picarto', key=key)
        if result:
            entry = {
                'picarto_url': url,
                'member_id': key
            }
        else:
            entry = {
                'picarto_url': url,
                'servers': [str(ctx.message.guild.id)],
                'notifications_on': 1,
                'live': 0,
                'member_id': key
            }
        self.bot.db.save('picarto', entry)
        await ctx.send(
            "I have just saved your Picarto URL {}, this guild will now be notified when you go live".format(
                ctx.message.author.mention))

    @picarto.command(name='remove', aliases=['delete'])
    @utils.custom_perms(send_messages=True)
    async def remove_picarto_url(self, ctx):
        """Removes your picarto URL"""
        entry = {
            'picarto_url': None,
            'member_id': str(ctx.message.author.id)
        }

        self.bot.db.save('picarto', entry)
        await ctx.send("I am no longer saving your picarto URL {}".format(ctx.message.author.mention))

    @picarto.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to turn picarto notifications on or off
        Call this command by itself, to add this guild to the list of guilds to be notified

        EXAMPLE: !picarto notify
        RESULT: This guild will now be notified of you going live"""
        key = str(ctx.message.author.id)
        servers = self.bot.db.load('picarto', key=key, pluck='servers')
        # Check if this user is saved at all
        if servers is None:
            await ctx.send(
                "I do not have your Picarto URL added {}. You can save your Picarto url with !picarto add".format(
                    ctx.message.author.mention))
        # Then check if this guild is already added as one to notify in
        elif str(ctx.message.guild.id) in servers:
            await ctx.send("I am already set to notify in this guild...")
        else:
            servers.append(str(ctx.message.guild.id))
            entry = {
                'member_id': key,
                'servers': servers
            }
            self.bot.db.save('picarto', entry)
            await ctx.send("This server will now be notified if you go live")

    @notify.command(name='on', aliases=['start,yes'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns picarto notifications on

        EXAMPLE: !picarto notify on
        RESULT: Notifications are sent when you go live"""
        key = str(ctx.message.author.id)
        result = self.bot.db.load('picarto', key=key)
        if result:
            entry = {
                'member_id': key,
                'notifications_on': 1
            }
            self.bot.db.save('picarto', entry)
            await ctx.send("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))
        else:
            await ctx.send("I can't notify if you go live if I don't know your picarto URL yet!")

    @notify.command(name='off', aliases=['stop,no'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns picarto notifications off

        EXAMPLE: !picarto notify off
        RESULT: No more notifications sent when you go live"""
        key = str(ctx.message.author.id)
        result = self.bot.db.load('picarto', key=key)
        if result:
            entry = {
                'member_id': key,
                'notifications_on': 0
            }
            self.bot.db.save('picarto', entry)
            await ctx.send(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))
        else:
            await ctx.send(
                "I mean, I'm already not going to notify anyone, because I don't have your picarto URL saved...")


def setup(bot):
    p = Picarto(bot)
    bot.loop.create_task(p.check_channels())
    bot.add_cog(Picarto(bot))
