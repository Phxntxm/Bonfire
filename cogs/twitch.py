from discord.ext import commands
from .utils import config
import discord
import re

class Twitch:
    """Class for some twitch integration"""
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(pass_context=True,no_pm=True)
    async def twitch(self, ctx, *, member : discord.Member = None):
        pass
        if member is not None:
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_default))
            cursor.execute('select twitch_url from twitch where user_id="{}"'.format(member.id))
            result = cursor.fetchone()
            if result is not None:
                await bot.say("{}'s twitch URL is {}'".format(member.name,result['twitch_url']))
                config.closeConnection()
            else:
                await bot.say("{} has not savede their twitch URL yet!")
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
        
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('update twitch set twitch_url={} from twitch where user_id="{}"'.format(url,ctx.message.author.id))
        else:
            cursor.execute('insert into twitch (user_id,server_id,twitch_url,notifications_on) values ("{}","{}","{}",1)'
                .format(ctx.message.author.id,ctx.message.server.id,url))
        await self.bot.say("I have just saved your twitch url {}".format(ctx.message.author.mention))
        config.closeConnection()
    
    @twitch.command(name='remove',aliases=['delete'],pass_context=True,no_pm=True)
    async def remove_twitch_url(self,ctx):
        """Removes your twitch URL"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select twitch_url from twitch where user_id="{}"'.format(ctx.message.author.id))
        result = cursor.fetchone()
        if result is not None:
            cursor.execute('delete from twitch where user_id="{}"'.format(url,ctx.message.author.id))
        else:
            await bot.say("I do not have your twitch URL added {}".format(ctx.message.author.mention))
            config.closeConnection()
            
def setup(bot)
    bot.add_cog(Twitch(bot))
