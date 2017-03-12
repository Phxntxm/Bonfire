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

    async def channel_online(self, twitch_url: str):
        # Check a specific channel's data, and get the response in text format
        channel = re.search("(?<=twitch.tv/)(.*)", twitch_url).group(1)
        url = "https://api.twitch.tv/kraken/streams/{}".format(channel)

        response = await utils.request(url, payload=self.params)

        # For some reason Twitch's API call is not reliable, sometimes it returns stream as None
        # That is what we're checking specifically, sometimes it doesn't exist in the returned JSON at all
        # Sometimes it returns something that cannot be decoded with JSON (which means we'll get None back)
        # In either error case, just assume they're offline, the next check will most likely work
        try:
            return response['stream'] is not None
        except (KeyError, TypeError):
            return False

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # Loop through as long as the bot is connected
        try:
            while not self.bot.is_closed():
                twitch = await utils.filter_content('twitch', {'notifications_on': 1})
                for data in twitch:
                    m_id = int(data['member_id'])
                    url = data['twitch_url']
                    # Check if they are online
                    online = await self.channel_online(url)
                    # If they're currently online, but saved as not then we'll send our notification
                    if online and data['live'] == 0:
                        for s_id in data['servers']:
                            s_id = int(s_id)
                            server = self.bot.get_guild(s_id)
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            server_settings = await utils.get_content('server_settings', s_id)
                            channel_id = int(server_settings.get('notification_channel', s_id))
                            channel = server.get_channel(channel_id)
                            await channel.send("{} has just gone live! View their stream at <{}>".format(member.display_name, data['twitch_url']))
                            self.bot.loop.create_task(utils.update_content('twitch', {'live': 1}, str(m_id)))
                    elif not online and data['live'] == 1:
                        for s_id in data['servers']:
                            s_id = int(s_id)
                            server = self.bot.get_guild(s_id)
                            if server is None:
                                continue
                            member = server.get_member(m_id)
                            if member is None:
                                continue
                            server_settings = await utils.get_content('server_settings', s_id)
                            channel_id = int(server_settings.get('notification_channel', s_id))
                            channel = server.get_channel(channel_id)
                            await channel.send("{} has just gone offline! View their stream next time at <{}>".format(member.display_name, data['twitch_url']))
                            self.bot.loop.create_task(utils.update_content('twitch', {'live': 0}, str(m_id)))
                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def twitch(self, ctx, *, member: discord.Member = None):
        """Use this command to check the twitch info of a user

        EXAMPLE: !twitch @OtherPerson
        RESULT: Information about their twitch URL"""
        await ctx.message.channel.trigger_typing()

        if member is None:
            member = ctx.message.author

        result = await utils.get_content('twitch', str(member.id))
        if result is None:
            await ctx.send("{} has not saved their twitch URL yet!".format(member.name))
            return

        url = result['twitch_url']
        user = re.search("(?<=twitch.tv/)(.*)", url).group(1)
        twitch_url = "https://api.twitch.tv/kraken/channels/{}".format(user)
        payload = {'client_id': self.key}
        data = await utils.request(twitch_url, payload=payload)

        embed = discord.Embed(title=data['display_name'], url=url)
        if data['logo']:
            embed.set_thumbnail(url=data['logo'])

        embed.add_field(name='Title', value=data['status'])
        embed.add_field(name='Followers', value=data['followers'])
        embed.add_field(name='Views', value=data['views'])
        if data['game']:
            embed.add_field(name='Game', value=data['game'])
        embed.add_field(name='Language', value=data['broadcaster_language'])

        await ctx.send(embed=embed)

    @twitch.command(name='add', no_pm=True)
    @utils.custom_perms(send_messages=True)
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
        entry = {'twitch_url': url,
                 'servers': [str(ctx.message.guild.id)],
                 'notifications_on': 1,
                 'live': 0,
                 'member_id': key}
        update = {'twitch_url': url}

        # Check to see if this user has already saved a twitch URL
        # If they have, update the URL, otherwise create a new entry
        # Assuming they're not live, and notifications should be on
        if not await utils.add_content('twitch', entry):
            await utils.update_content('twitch', update, key)
        await ctx.send("I have just saved your twitch url {}".format(ctx.message.author.mention))

    @twitch.command(name='remove', aliases=['delete'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL

        EXAMPLE: !twitch remove
        RESULT: I stop saving your twitch URL"""
        # Just try to remove it, if it doesn't exist, nothing is going to happen
        await utils.remove_content('twitch', str(ctx.message.author.id))
        await ctx.send("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))

    @twitch.group(no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to modify notification settings for your twitch user
        Call this command by itself to add 'this' server as one that will be notified when you on/offline

        EXAMPLE: !twitch notify
        RESULT: This server will now be notified when you go live"""
        key = str(ctx.message.author.id)
        result = await utils.get_content('twitch', key)
        # Check if this user is saved at all
        if result is None:
            await ctx.send(
                "I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(
                    ctx.message.author.mention))
        # Then check if this server is already added as one to notify in
        elif str(ctx.message.guild.id) in result['servers']:
            await ctx.send("I am already set to notify in this server...")
        else:
            await utils.update_content('twitch', {'servers': r.row['servers'].append(str(ctx.message.guild.id))}, key)
            await ctx.send("This server will now be notified if you go live")

    @notify.command(name='on', aliases=['start,yes'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns twitch notifications on

        EXAMPLE: !twitch notify on
        RESULT: Notifications will be sent when you go live"""
        if await utils.update_content('twitch', {"notifications_on": 1}, str(ctx.message.author.id)):
            await ctx.send("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
                ctx.message.author.mention))
        else:
            await ctx.send("I can't notify if you go live if I don't know your twitch URL yet!")

    @notify.command(name='off', aliases=['stop,no'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns twitch notifications off

        EXAMPLE: !twitch notify off
        RESULT: Notifications will not be sent when you go live"""
        if await utils.update_content('twitch', {"notifications_on": 1}, str(ctx.message.author.id)):
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
