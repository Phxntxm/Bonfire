import aiohttp
import json
import asyncio

from .utils import config

base_url = 'https://ptvappapi.picarto.tv'
key = '03e26294-b793-11e5-9a41-005056984bd4'

async def check_online(stream):
    try:
        url = '{}/channel/{}?key={}'.format(base_url,stream,key)
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
            #Do the things
            pass
        await asyncio.sleep(30)
    
def setup(bot):
    p = Picarto(bot)
    config.loop.create_task(p.checkChannels())
    bot.add_cog(Picarto(bot))
