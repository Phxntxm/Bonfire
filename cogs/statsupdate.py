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
        server_count = 0
        data = await config.get_content('bot_data')

        for entry in data:
            server_count += entry.get('server_count')

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
        r_filter = {'shard_id': config.shard_id}
        server_count = len(self.bot.servers)
        member_count = len(set(self.bot.get_all_members()))
        entry = {'server_count': server_count, 'member_count': member_count, "shard_id": config.shard_id}
        # Check if this was successful, if it wasn't, that means a new shard was added and we need to add that entry
        if not await config.update_content('bot_data', entry, r_filter):
            await config.add_content('bot_data', entry, r_filter)
        self.bot.loop.create_task(self.update())

    async def on_server_leave(self, server):
        r_filter = {'shard_id': config.shard_id}
        server_count = len(self.bot.servers)
        member_count = len(set(self.bot.get_all_members()))
        entry = {'server_count': server_count, 'member_count': member_count, "shard_id": config.shard_id}
        # Check if this was successful, if it wasn't, that means a new shard was added and we need to add that entry
        if not await config.update_content('bot_data', entry, r_filter):
            await config.add_content('bot_data', entry, r_filter)
        self.bot.loop.create_task(self.update())

    async def on_ready(self):
        r_filter = {'shard_id': config.shard_id}
        server_count = len(self.bot.servers)
        member_count = len(set(self.bot.get_all_members()))
        entry = {'server_count': server_count, 'member_count': member_count, "shard_id": config.shard_id}
        # Check if this was successful, if it wasn't, that means a new shard was added and we need to add that entry
        if not await config.update_content('bot_data', entry, r_filter):
            await config.add_content('bot_data', entry, r_filter)
        self.bot.loop.create_task(self.update())


def setup(bot):
    bot.add_cog(StatsUpdate(bot))
