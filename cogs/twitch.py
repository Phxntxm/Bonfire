from discord.ext import commands

from . import utils

import aiohttp
import asyncio
import discord
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
        self.key = utils.twitch_key
        self.params = {'client_id': self.key}

    def _form_embed(self, data):
        if not data:
            return None
        # I want to make the least API calls possible, however there's a few things to note here:
        # 1) When requesting /streams and a channel is offline, the channel data is not provided
        # 2) When requesting /streams and a channel is online, the channel data is provided
        # 3) When requesting /channels, no data is provided about the channel being on or offline
        # 4) The data provide in /streams matches /channels when they are online
        # Due to this...the data "source" will be different based on if they are on or offline
        # Instead of making an API call to see if they're online, then an API call to get the data
        # The idea here is to separate creating the embed, and the getting of data
        # With this method, I can get the data if they are online,then return the embed if applicable
        embed = discord.Embed(title=data['display_name'], url=data['url'])
        if data['logo']:
            embed.set_thumbnail(url=data['logo'])

        embed.add_field(name='Title', value=data['status'])
        embed.add_field(name='Followers', value=data['followers'])
        embed.add_field(name='Views', value=data['views'])
        if data['game']:
            embed.add_field(name='Game', value=data['game'])
        embed.add_field(name='Language', value=data['broadcaster_language'])

        return embed

    async def online_embed(self, twitch_url):
        # First make sure the twitch URL is actually given
        if not twitch_url:
            return None

        # Check a specific channel's data, and get the response in text format
        channel = re.search("(?<=twitch.tv/)(.*)", twitch_url).group(1)
        url = "https://api.twitch.tv/kraken/streams/{}".format(channel)

        response = await utils.request(url, payload=self.params)

        # For some reason Twitch's API call is not reliable, sometimes it returns stream as None
        # That is what we're checking specifically, sometimes it doesn't exist in the returned JSON at all
        # Sometimes it returns something that cannot be decoded with JSON (which means we'll get None back)
        # In either error case, just assume they're offline, the next check will most likely work
        try:
            data = response['stream']['channel']
            embed = self._form_embed(data)
            return embed
        except (KeyError, TypeError):
            return None

    async def offline_embed(self, twitch_url):
        # First make sure the twitch URL is actually given
        if not twitch_url:
            return None

        # Check a specific channel's data, and get the response in text format
        channel = re.search("(?<=twitch.tv/)(.*)", twitch_url).group(1)
        url = "https://api.twitch.tv/kraken/channels/{}".format(channel)

        data = await utils.request(url, payload=self.params)
        return self._form_embed(data)

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # This is a loop that runs every 30 seconds, checking if anyone has gone online
        try:
            while not self.bot.is_closed():
                twitch = await self.bot.db.actual_load('twitch', table_filter={'notifications_on': 1})
                for data in twitch:
                    m_id = int(data['member_id'])
                    url = data['twitch_url']
                    # Check if they are online by trying to get an displayed embed for this user
                    embed = await self.online_embed(url)
                    # If they're currently online, but saved as not then we'll let servers know they are now online
                    if embed and data['live'] == 0:
                        msg = "{member.display_name} has just gone live!"
                        self.bot.db.save('twitch', {'live': 1, 'member_id': str(m_id)})
                    # Otherwise our notification will say they've gone offline
                    elif not embed and data['live'] == 1:
                        msg = "{member.display_name} has just gone offline!"
                        embed = await self.offline_embed(url)
                        self.bot.db.save('twitch', {'live': 0, 'member_id': str(m_id)})
                    else:
                        continue

                    # Loop through each server that they are set to notify
                    for s_id in data['servers']:
                        server = self.bot.get_guild(int(s_id))
                        # If we can't find it, ignore this one
                        if server is None:
                            continue
                        member = server.get_member(m_id)
                        # If we can't find them in this server, also ignore
                        if member is None:
                            continue

                        # Get the notifications settings, get the twitch setting
                        notifications = self.bot.db.load('server_settings', key=s_id, pluck='notifications') or {}
                        # Set our default to either the one set, or the default channel of the server
                        default_channel_id = notifications.get('default') or s_id
                        # If it is has been overriden by twitch notifications setting, use this
                        channel_id = notifications.get('twitch') or default_channel_id
                        # Now get the channel
                        channel = server.get_channel(int(channel_id))
                        # Unfortunately we need one more check, to ensure a channel hasn't been chosen, then deleted
                        if channel is None:
                            channel = server.default_channel

                        # Then just send our message
                        try:
                            await channel.send(msg.format(member=member), embed=embed)
                        except (discord.Forbidden, discord.HTTPException):
                            pass

                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def twitch(self, ctx, *, member: discord.Member = None):
        """Use this command to check the twitch info of a user

        EXAMPLE: !twitch @OtherPerson
        RESULT: Information about their twitch URL"""
        await ctx.message.channel.trigger_typing()

        if member is None:
            member = ctx.message.author

        url = self.bot.db.load('twitch', key=member.id, pluck='twitch_url')
        if url is None:
            await ctx.send("{} has not saved their twitch URL yet!".format(member.name))
            return

        embed = await self.offline_embed(url)
        await ctx.send(embed=embed)

    @twitch.command(name='add')
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL

        EXAMPLE: !twitch add MyTwitchName
        RESULT: Saves your twitch URL; notifications will be sent to this server when you go live"""
        await ctx.message.channel.trigger_typing()

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
        status = await utils.request(url, attr='status')
        if not status == 200:
            await ctx.send("That twitch user does not exist! "
                           "What would be the point of adding a nonexistant twitch user? Silly")
            return

        key = str(ctx.message.author.id)

        # Check if it exists first, if it does we don't want to override some of the settings
        result = self.bot.db.load('twitch', key=key)
        if result:
            entry = {
                'twitch_url': url,
                'member_id': key
            }
        else:
            entry = {
                'twitch_url': url,
                'servers': [str(ctx.message.guild.id)],
                'notifications_on': 1,
                'live': 0,
                'member_id': key
            }
        self.bot.db.save('twitch', entry)
        await ctx.send("I have just saved your twitch url {}".format(ctx.message.author.mention))

    @twitch.command(name='remove', aliases=['delete'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL

        EXAMPLE: !twitch remove
        RESULT: I stop saving your twitch URL"""
        entry = {
            'twitch_url': None,
            'member_id': str(ctx.message.author.id)
        }

        self.bot.db.save('twitch', entry)
        await ctx.send("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))

    @twitch.command(name='alerts', aliases=['notifications'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def twitch_alerts_channel(self, ctx, channel: discord.TextChannel):
        """Sets the notifications channel for twitch notifications

        EXAMPLE: !twitch alerts #twitch
        RESULT: Twitch notifications will go to this channel
        """
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications': {
                'twitch': str(channel.id)
            }
        }
        self.bot.db.save('server_settings', entry)
        await ctx.send("All Twitch notifications will now go to {}".format(channel.mention))

    @twitch.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def notify(self, ctx):
        """This can be used to modify notification settings for your twitch user
        Call this command by itself to add 'this' server as one that will be notified when you on/offline

        EXAMPLE: !twitch notify
        RESULT: This server will now be notified when you go live"""
        key = str(ctx.message.author.id)
        servers = self.bot.db.load('twitch', key=key, pluck='servers')
        # Check if this user is saved at all
        if servers is None:
            await ctx.send(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        # Then check if this server is already added as one to notify in
        elif str(ctx.message.guild.id) in servers:
            await ctx.send("I am already set to notify in this server...")
        else:
            servers.append(str(ctx.message.guild.id))
            entry = {
                'member_id': key,
                'servers': servers
            }
            self.bot.db.save('twitch', entry)
            await ctx.send("This server will now be notified if you go live")

    @notify.command(name='on', aliases=['start,yes'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def notify_on(self, ctx):
        """Turns twitch notifications on

        EXAMPLE: !twitch notify on
        RESULT: Notifications will be sent when you go live"""
        key = str(ctx.message.author.id)
        result = self.bot.db.load('twitch', key=key)
        if result:
            entry = {
                'member_id': key,
                'notifications_on': 1
            }
            self.bot.db.save('twitch', entry)
            await ctx.send("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))
        else:
            await ctx.send("I can't notify if you go live if I don't know your twitch URL yet!")

    @notify.command(name='off', aliases=['stop,no'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def notify_off(self, ctx):
        """Turns twitch notifications off

        EXAMPLE: !twitch notify off
        RESULT: Notifications will not be sent when you go live"""
        key = str(ctx.message.author.id)
        result = self.bot.db.load('twitch', key=key)
        if result:
            entry = {
                'member_id': key,
                'notifications_on': 0
            }
            self.bot.db.save('twitch', entry)
            await ctx.send(
                "I will not notify if you go live anymore {}, "
                "are you going to stream some lewd stuff you don't want people to see?~".format(
                    ctx.message.author.mention))
        else:
            await ctx.send(
                "I mean, I'm already not going to notify anyone, because I don't have your twitch URL saved...")


def setup(bot):
    t = Twitch(bot)
    bot.loop.create_task(t.check_channels())
    bot.add_cog(Twitch(bot))
