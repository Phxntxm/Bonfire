from .utils import config
import aiohttp
import logging
import json

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

    async def on_server_join(self, server):
        self.bot.loop.create_task(self.update())

    async def on_server_leave(self, server):
        self.bot.loop.create_task(self.update())

    async def on_ready(self):
        self.bot.loop.create_task(self.update())

    async def on_member_join(self, member):
        guild = member.guild
        server_settings = await config.get_content('server_settings', str(guild.id))

        try:
            join_leave_on = server_settings['join_leave']
            if join_leave_on:
                channel_id = server_settings['notification_channel'] or member.guild.id
            else:
                return
        except (IndexError, TypeError):
            return

        channel = guild.get_channel(int(channel_id))
        await channel.send("Welcome to the '{0.guild.name}' server {0.mention}!".format(member))

    async def on_member_remove(self, member):
        guild = member.guild
        server_settings = await config.get_content('server_settings', str(guild.id))

        try:
            join_leave_on = server_settings['join_leave']
            if join_leave_on:
                channel_id = server_settings['notification_channel'] or member.guild.id
            else:
                return
        except (IndexError, TypeError):
            return

        channel = guild.get_channel(int(channel_id))
        await channel.send("{0} has left the server, I hope it wasn't because of something I said :c".format(member.display_name))


def setup(bot):
    bot.add_cog(StatsUpdate(bot))
