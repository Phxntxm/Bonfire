import aiohttp
import json
import asyncio
import discord

from discord.ext import commands
from .utils import config
from .utils import checks

base_url = 'https://ptvappapi.picarto.tv'

#This is a public key for use, I don't care if this is seen
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
    
    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.customPermsOrRole(send_messages=True)
    async def picarto(self, ctx, member: discord.Member=None):
        """This command can be used to view Picarto stats about a certain member"""
        member = member or ctx.message.author
        picarto_urls = config.getContent('picarto') or {}
        member_url = picarto_urls.get(member.id)
        if not member_url:
            await self.bot.say("That user does not have a picarto url setup!")
            return
        
        with aiohttp.ClientSession(headers={"User-Agent": "Bonfire/1.0.0"}) as s:
            async with s.get(member_url) as r:
                response = await r.text()
        data = json.loads(response)
        things_to_print = ['channel','commissions_enabled','is_nsfw','program','tablet','followers','content_type']
        fmt = "\n".join("{}: {}".format(i, r) for i,r in data.items() if i in things_to_print)
        await self.bot.say("Picarto stats for {}: ```\n{}```".format(member.display_name, fmt))
        
    @picarto.command(name='add', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def add_picarto_url(self, ctx, url: str):
        """Saves your user's picarto URL"""
        try:
            url = re.search("((?<=://)?picarto.tv/)+(.*)", url).group(0)
        except AttributeError:
            url = "https://www.picarto.tv/{}".format(url)
        else:
            url = "https://www.{}".format(url)
        
        api_url = '{}/channel/{}?key={}'.format(base_url,re.search("https://www.picarto.tv/(.*)",url).group(1),key)
        
        with aiohttp.ClientSession() as s:
            async with s.get(api_url) as r:
                if not r.status == 200:
                    await self.bot.say("That Picarto user does not exist! "
                                       "What would be the point of adding a nonexistant Picarto user? Silly")
                    return

        picarto_urls = config.getContent('picarto') or {}
        result = picarto_urls.get(ctx.message.author.id)

        if result is not None:
            picarto_urls[ctx.message.author.id]['picarto_url'] = url
        else:
            picarto_urls[ctx.message.author.id] = {'picarto_url': url, 'server_id': ctx.message.server.id,
                                             'notifications_on': 1, 'live': 0}
        config.saveContent('picarto', picarto_urls)
        await self.bot.say("I have just saved your Picarto url {}".format(ctx.message.author.mention))
        
def setup(bot):
    p = Picarto(bot)
    #config.loop.create_task(p.check_channels())
    bot.add_cog(Picarto(bot))
