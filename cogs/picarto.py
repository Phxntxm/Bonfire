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


async def online_users():
    try:
        # Someone from picarto contacted me and told me their database queries are odd
        # It is more efficent on their end to make a query for all online users, and base checks off that
        # In place of requesting for /channel and checking if that is online currently, for each channel
        # This method is in place to just return all online_users
        url = BASE_URL + '/online/all'
        payload = {'key': api_key}
        return await utils.request(url, payload=payload)
    except:
        return {}


def check_online(online_channels, channel):
    # online_channels is the dictionary of all users online currently
    # And channel is the name we are checking against that
    # This creates a list of all users that match this channel name (should only ever be 1)
    # And returns True as long as it is more than 0
    matches = [stream for stream in online_channels if stream['channel_name'].lower() == channel.lower()]
    return len(matches) > 0


class Picarto:
    def __init__(self, bot):
        self.bot = bot

    async def check_channels(self):
        await self.bot.wait_until_ready()
        # This is a loop that runs every 30 seconds, checking if anyone has gone online
        try:
            while not self.bot.is_closed:
                r_filter = {'notifications_on': 1}
                picarto = await utils.filter_content('picarto', r_filter)
                # Get all online users before looping, so that only one request is needed
                online_users_list = await online_users()
                old_online_users = {data['member_id']: data for data in picarto if data['live']}
                old_offline_users = {data['member_id']: data for data in picarto if not data['live']}

                for m_id, result in old_offline_users.items():
                    # Get their url and their user based on that url
                    url = result['picarto_url']
                    user = re.search("(?<=picarto.tv/)(.*)", url).group(1)
                    # Check if they are online right now
                    if check_online(online_users_list, user):
                        for guild_id in result['servers']:
                            # Get the channel to send the message to, based on the saved alert's channel
                            guild = self.bot.get_guild(guild_id)
                            if guild is None:
                                continue
                            guild_alerts = await utils.get_content('server_alerts', {'server_id': guild_id})
                            try:
                                channel_id = guild_alerts['channel_id']
                            except (IndexError, TypeError):
                                channel_id = guild_id
                            channel = self.bot.get_channel(channel_id)
                            # Get the member that has just gone live
                            member = guild.get_member(m_id)
                            if member is None:
                                continue

                            fmt = "{} has just gone live! View their stream at {}".format(member.display_name, url)
                            await channel.send(fmt)
                        await utils.update_content('picarto', {'live': 1}, {'member_id': m_id})
                for m_id, result in old_online_users.items():
                    # Get their url and their user based on that url
                    url = result['picarto_url']
                    user = re.search("(?<=picarto.tv/)(.*)", url).group(1)
                    # Check if they are online right now
                    if not check_online(online_users_list, user):
                        for guild_id in result['servers']:
                            # Get the channel to send the message to, based on the saved alert's channel
                            guild = self.bot.get_guild(guild_id)
                            if guild is None:
                                continue
                            guild_alerts = await utils.get_content('server_alerts', {'server_id': guild_id})
                            try:
                                channel_id = guild_alerts['channel_id']
                            except (IndexError, TypeError):
                                channel_id = guild_id
                            channel = self.bot.get_channel(channel_id)
                            # Get the member that has just gone live
                            member = guild.get_member(m_id)
                            if member is None:
                                continue

                            fmt = "{} has just gone offline! Catch them next time they stream at {}".format(
                                member.display_name, url)
                            await channel.send(fmt)
                        await utils.update_content('picarto', {'live': 0}, {'member_id': m_id})
                await asyncio.sleep(30)
        except Exception as e:
            tb = traceback.format_exc()
            fmt = "{1}\n{0.__class__.__name__}: {0}".format(tb, e)
            log.error(fmt)

    @commands.group(invoke_without_command=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def picarto(self, ctx, member: discord.Member = None):
        """This command can be used to view Picarto stats about a certain member

        EXAMPLE: !picarto @otherPerson
        RESULT: Info about their picarto stream"""
        # If member is not given, base information on the author
        member = member or ctx.message.author
        picarto_entry = await utils.get_content('picarto', str(member.id))
        if picarto_entry is None:
            await ctx.send("That user does not have a picarto url setup!")
            return

        member_url = picarto_entry['picarto_url']

        # Use regex to get the actual username so that we can make a request to the API
        stream = re.search("(?<=picarto.tv/)(.*)", member_url).group(1)
        url = BASE_URL + '/channel/{}'.format(stream)
        payload = {'key': api_key}

        data = await utils.request(url, payload=payload)
        if data is None:
            await ctx.send("I couldn't connect to Picarto!")
            return

        # Not everyone has all these settings, so use this as a way to print information if it does, otherwise ignore it
        things_to_print = ['channel', 'commissions_enabled', 'is_nsfw', 'program', 'tablet', 'followers',
                           'content_type']

        embed = discord.Embed(title='{}\'s Picarto'.format(data['channel']), url=url)
        if data['avatar_url']:
            embed.set_thumbnail(url=data['avatar_url'])

        for i, result in data.items():
            if i in things_to_print:
                result = str(result)
                if not result:
                    result = '\u200B'

                embed.add_field(name=i, value=result)

        # Social URL's can be given if a user wants them to show
        # Print them if they exist, otherwise don't try to include them
        social_links = data.get('social_urls')

        for i, result in data['social_urls'].items():
            embed.add_field(name=i, value=result)

        await ctx.send(embed=embed)

    @picarto.command(name='add', no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def add_picarto_url(self, ctx, url: str):
        """Saves your user's picarto URL

        EXAMPLE: !picarto add MyUsername
        RESULT: Your picarto stream is saved, and notifications should go to this guild"""
        # This uses a lookbehind to check if picarto.tv exists in the url given
        # If it does, it matches picarto.tv/user and sets the url as that
        # Then (in the else) add https://www. to that
        # Otherwise if it doesn't match, we'll hit an AttributeError due to .group(0)
        # This means that the url was just given as a user (or something complete invalid)
        # So set URL as https://www.picarto.tv/[url]
        # Even if this was invalid such as https://www.picarto.tv/twitch.tv/user
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
            await ctx.send("That Picarto user does not exist! What would be the point of adding a nonexistant Picarto "
                           "user? Silly")
            return

        key = str(ctx.message.author.id)
        entry = {'picarto_url': url,
                 'servers': [str(ctx.message.guild.id)],
                 'notifications_on': 1,
                 'live': 0,
                 'member_id': key}
        if await utils.add_content('picarto', entry):
            await ctx.send(
                "I have just saved your Picarto URL {}, this guild will now be notified when you go live".format(
                    ctx.message.author.mention))
        else:
            await utils.update_content('picarto', {'picarto_url': url}, key)
            await ctx.send("I have just updated your Picarto URL")

    @picarto.command(name='remove', aliases=['delete'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def remove_picarto_url(self, ctx):
        """Removes your picarto URL"""
        if await utils.remove_content('picarto', str(ctx.message.author.id)):
            await ctx.send("I am no longer saving your picarto URL {}".format(ctx.message.author.mention))
        else:
            await ctx.send(
                "I do not have your picarto URL added {}. You can save your picarto url with {}picarto add".format(
                    ctx.message.author.mention, ctx.prefix))

    @picarto.group(no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def notify(self, ctx):
        """This can be used to turn picarto notifications on or off
        Call this command by itself, to add this guild to the list of guilds to be notified

        EXAMPLE: !picarto notify
        RESULT: This guild will now be notified of you going live"""
        key = str(ctx.message.author.id)
        result = await utils.get_content('picarto', key)
        # Check if this user is saved at all
        if result is None:
            await ctx.send(
                "I do not have your Picarto URL added {}. You can save your Picarto url with !picarto add".format(
                    ctx.message.author.mention))
        # Then check if this guild is already added as one to notify in
        elif ctx.message.guild.id in result['servers']:
            await ctx.send("I am already set to notify in this guild...")
        else:
            await utils.update_content('picarto', {'servers': r.row['servers'].append(str(ctx.message.guild.id))}, key)

    @notify.command(name='on', aliases=['start,yes'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def notify_on(self, ctx):
        """Turns picarto notifications on

        EXAMPLE: !picarto notify on
        RESULT: Notifications are sent when you go live"""
        await utils.update_content('picarto', {'notifications_on': 1}, str(ctx.message.author.id))
        await ctx.send("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(
            ctx.message.author.mention))

    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def notify_off(self, ctx):
        """Turns picarto notifications off

        EXAMPLE: !picarto notify off
        RESULT: No more notifications sent when you go live"""
        await utils.update_content('picarto', {'notifications_on': 0}, str(ctx.message.author.id))
        await ctx.send(
            "I will not notify if you go live anymore {}, "
            "are you going to stream some lewd stuff you don't want people to see?~".format(
                ctx.message.author.mention))


def setup(bot):
    p = Picarto(bot)
    bot.loop.create_task(p.check_channels())
    bot.add_cog(Picarto(bot))
