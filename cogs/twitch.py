from discord.ext import commands
from .utils import config
import urllib.request
import urllib.parse
import asyncio
import discord
import json
import re

def channelOnline(channel: str):
    url = "https://api.twitch.tv/kraken/streams/{}".format(channel)
    response = urllib.request.urlopen(url)
    data = json.loads(response.read().decode('utf-8'))
    return data['stream'] is not None
    
async def checkChannels(bot):
    await bot.wait_until_ready()
    cursor = config.getCursor()
    cursor.execute('use {}'.format(config.db_default))
    cursor.execute('select * from twitch')
    result = cursor.fetchall()
    for r in result:
        server = discord.utils.find(lambda s: s.id == r['server_id'], bot.servers)
        member = discord.utils.find(lambda m: m.id == r['user_id'], server.members)
        url = r['twitch_url']
        live = int(r['live'])
        notify = int(r['notifications_on'])
        user = re.search("(?<=twitch.tv/)(.*)",url).group(1)
        if not live and notify and channelOnline(user):
            cursor.execute('update twitch set live=1 where user_id="{}"'.format(r['user_id']))
            await bot.send_message(server,"{} has just gone live! View their stream at {}".format(member.name,url))
        elif live and not channelOnline(user):
            cursor.execute('update twitch set live=0 where user_id="{}"'.format(r['user_id']))
            await bot.send_message(server,"{} has just gone offline! Catch them next time they stream at {}".format(member.name,url))
    config.closeConnection()
    await asyncio.sleep(180)
            
    
class Twitch:
    """Class for some twitch integration
    You can add or remove your twitch stream for your user
    I will then notify the server when you have gone live or offline"""
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(pass_context=True,no_pm=True,invoke_without_command=True)
    async def twitch(self, ctx, *, member : discord.Member = None):
        """Use this command to check the twitch stream of a user"""
        pass
        if member is not None:
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_default))
            cursor.execute('select twitch_url from twitch where user_id="{}"'.format(member.id))
            result = cursor.fetchone()
            if result is not None:
                await self.bot.say("{}'s twitch URL is {}".format(member.name,result['twitch_url']))
                config.closeConnection()
            else:
                await self.bot.say("{} has not saved their twitch URL yet!".format(member.name))
                config.closeConnection()
    
    @twitch.command(name='add',pass_context=True,no_pm=True)
    async def add_twitch_url(self, ctx, url: str):
        """Saves your user's twitch URL"""
        try:
            url=re.search("((?<=://)?twitch.tv/)+(.*)",url).group(0)
        except AttributeError:
            url="https://www.twitch.tv/{}".format(url)
        else:
            url="https://www.{}".format(url)
            
        try:
            urllib.request.urlopen(url)
        except urllib.request.HTTPError:
            await self.bot.say("That twitch user does not exist! What would be the point of adding a nonexistant twitch user? Silly")
            return
            
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('update twitch set twitch_url="{}" where user_id="{}"'.format(url,ctx.message.author.id))
        else:
            cursor.execute('insert into twitch (user_id,server_id,twitch_url,notifications_on,live) values ("{}","{}","{}",1,0)'
                .format(ctx.message.author.id,ctx.message.server.id,url))
        await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))
        config.closeConnection()
    
    @twitch.command(name='remove',aliases=['delete'],pass_context=True,no_pm=True)
    async def remove_twitch_url(self, ctx):
        """Removes your twitch URL"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('delete from twitch where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say("I am no longer saving your twitch URL {}".format(ctx.message.author.mention))
            config.closeConnection()
        else:
            await self.bot.say("I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(ctx.message.author.mention))
            config.closeConnection()
    
    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    async def notify(self, ctx):
        """This can be used to turn notifications on or off"""
        pass
        
    @notify.command(name='on', aliases=['start,yes'], pass_context=True, no_pm=True)
    async def notify_on(self, ctx):
        """Turns twitch notifications on"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select notifications_on from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(ctx.message.author.mention))
            config.closeConnection()
            return
        elif result:
            await self.bot.say("What do you want me to do, send two notifications? Not gonna happen {}".format(ctx.message.author.mention))
            config.closeConnection()
            return
        else:
            cursor.execute('update twitch set notifications_on=1 where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say("I will notify if you go live {}, you'll get a bajillion followers I promise c:".format(ctx.message.author.mention))
            config.closeConnection()
            return
            
    @notify.command(name='off', aliases=['stop,no'], pass_context=True, no_pm=True)
    async def notify_off(self, ctx):
        """Turns twitch notifications off"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select notifications_on from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("I do not have your twitch URL added {}. You can save your twitch url with !twitch add".format(ctx.message.author.mention))
            config.closeConnection()
            return
        elif not result:
            await self.bot.say("I am already set to not notify if you go live! Pay attention brah {}".format(ctx.message.author.mention))
            config.closeConnection()
            return
        else:
            cursor.execute('update twitch set notifications_on=0 where user_id="{}"'.format(ctx.message.author.id))
            await self.bot.say("I will not notify if you go live anymore {}, are you going to stream some lewd stuff you don't want people to see?~".format(ctx.message.author.mention))
            config.closeConnection()
            return
            
        
def setup(bot):
    bot.add_cog(Twitch(bot))
    config.loop.create_task(checkChannels(bot))
