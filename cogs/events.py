from .utils import config
import aiohttp
import logging
import json
import discord

log = logging.getLogger()

discord_bots_url = 'https://bots.discord.pw/api'
carbonitex_url = 'https://www.carbonitex.net/discord/data/botdata.php'


class StatsUpdate:
    """This is used purely to update stats information for carbonitex and botx.discord.pw"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def __unload(self):
        self.bot.loop.create_task(self.session.close())

    async def update(self):
        server_count = len(self.bot.guilds)

        carbon_payload = {
            'key': config.carbon_key,
            'servercount': server_count
        }

        async with self.session.post(carbonitex_url, data=carbon_payload) as resp:
            log.info('Carbonitex statistics returned {} for {}'.format(resp.status, carbon_payload))

        payload = json.dumps({
            'server_count': server_count
        })

        headers = {
            'authorization': config.discord_bots_key,
            'content-type': 'application/json'
        }

        url = '{}/bots/{}/stats'.format(discord_bots_url, self.bot.user.id)
        async with self.session.post(url, data=payload, headers=headers) as resp:
            log.info('bots.discord.pw statistics returned {} for {}'.format(resp.status, payload))

    async def on_guild_join(self, _):
        self.bot.loop.create_task(self.update())

    async def on_guild_leave(self, _):
        self.bot.loop.create_task(self.update())

    async def on_ready(self):
        self.bot.loop.create_task(self.update())

    async def on_member_join(self, member):
        guild = member.guild
        server_settings = self.bot.db.load('server_settings', key=str(guild.id))

        try:
            join_leave_on = server_settings['join_leave']
            if join_leave_on:
                # Get the notifications settings, get the welcome setting
                notifications = self.bot.db.load('server_settings', key=guild.id, pluck='notifications') or {}
                # Set our default to either the one set, or the default channel of the server
                default_channel_id = notifications.get('default')
                # If it is has been overriden by picarto notifications setting, use this
                channel_id = notifications.get('welcome') or default_channel_id
                # Get the message if it exists
                join_message = self.bot.db.load('server_settings', key=guild.id, pluck='welcome_message')
                if not join_message:
                    join_message = "Welcome to the '{server}' server {member}!"
            else:
                return
        except (IndexError, TypeError, KeyError):
            return

        if channel_id:
            channel = guild.get_channel(int(channel_id))
        else:
            return
        try:
            await channel.send(join_message.format(server=guild.name, member=member.mention))
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            pass

    async def on_member_remove(self, member):
        guild = member.guild
        server_settings = self.bot.db.load('server_settings', key=str(guild.id))

        try:
            join_leave_on = server_settings['join_leave']
            if join_leave_on:
                # Get the notifications settings, get the welcome setting
                notifications = self.bot.db.load('server_settings', key=guild.id, pluck='notifications') or {}
                # Set our default to either the one set, or the default channel of the server
                default_channel_id = notifications.get('default')
                # If it is has been overriden by picarto notifications setting, use this
                channel_id = notifications.get('welcome') or default_channel_id
                # Get the message if it exists
                leave_message = self.bot.db.load('server_settings', key=guild.id, pluck='goodbye_message')
                if not leave_message:
                    leave_message = "{member} has left the server, I hope it wasn't because of something I said :c"
            else:
                return
        except (IndexError, TypeError, KeyError):
            return

        if channel_id:
            channel = guild.get_channel(int(channel_id))
        else:
            return
        try:
            await channel.send(leave_message.format(server=guild.name, member=member.name))
        except (discord.Forbidden, discord.HTTPException, AttributeError):
            pass


def setup(bot):
    bot.add_cog(StatsUpdate(bot))
