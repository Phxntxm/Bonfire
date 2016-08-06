from .utils import config
import aiohttp
import logging
import json

log = logging.getLogger()

discord_bots_url = 'https://bots.discord.pw/api'


class StatsUpdate:
    """This is used purely to update stats information for carbonitex and botx.discord.pw"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def __unload(self):
        config.loop.create_task(self.session.close())

    async def update(self):
        payload = json.dumps({
            'server_count': len(self.bot.servers)
        })

        headers = {
            'authorization': config.discord_bots_key,
            'content-type': 'application/json'
        }

        url = '{0}/bots/{1.user.id}/stats'.format(discord_bots_url, self.bot)
        async with self.session.post(url, data=payload, headers=headers) as resp:
            log.info('bots.discord.pw statistics returned {0.status} for {1}'.format(resp, payload))

    async def on_server_join(self, server):
        await self.update()

    async def on_server_leave(self, server):
        await self.update()

    async def on_ready(self):
        await self.update()


def setup(bot):
    bot.add_cog(StatsUpdate(bot))
