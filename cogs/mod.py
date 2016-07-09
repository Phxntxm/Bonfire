from discord.ext import commands
from .utils import checks
from .utils import config
import pymysql


class Mod:
    """Commands that can be used by a or an admin, depending on the command"""
    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.command(pass_context=True)
    @checks.isMod()
    async def nsfw(self, ctx):
        """Registers this channel as a 'nsfw' channel''"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        try:
            cursor.execute('insert into nsfw_channels (channel_id) values ("{}")'.format(ctx.message.channel.id))
        except pymysql.IntegrityError:
            await self.bot.say("This channel is already registered as 'nsfw'!")
            return
        config.connection.commit()
        config.connection.close()
        await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")
    
    @commands.command(pass_context=True)
    @checks.isMod()
    async def unnsfw(self, ctx):
        """Removes this channel as a 'nsfw' channel"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        try:
            cursor.execute('delete from nsfw_channels where channel_id="{}"'.format(ctx.messsage.channel.id))
        except pymysql.IntegrityError:
            await self.bot.say("This channel is not registered as a ''nsfw' channel!")
            return
        config.connection.commit()
        config.connection.close()
        await self.bot.say("This channel has just been unregistered as a nsfw channel")
    
    @commands.command(pass_context=True, no_pm=True)
    @checks.isAdmin()
    async def leave(self, ctx):
        """Forces the bot to leave the server"""
        await self.bot.say('Why must I leave? Hopefully I can come back :c')
        await self.bot.leave_server(ctx.message.server)

    
    @commands.command()
    @checks.isAdmin()
    async def load(self, *, module : str):
        """Loads a module"""
        try:
            module = module.lower()
            if not module.startswith("cogs"):
                module = "cogs.{}".format(module)
            self.bot.load_extension(module)
            await self.bot.say("I have just loaded the {} module".format(module))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))
        
    @commands.command()
    @checks.isAdmin()
    async def unload(self, *, module : str):
        """Unloads a module"""
        try:
            module = module.lower()
            if not module.startswith("cogs"):
                module = "cogs.{}".format(module)
            self.bot.unload_extension(module)
            await self.bot.say("I have just unloaded the {} module".format(module))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))
        
    @commands.command()
    @checks.isAdmin()
    async def reload(self, *, module : str):
        """Reloads a module"""
        try:
            module = module.lower()
            if not module.startswith("cogs"):
                module = "cogs.{}".format(module)
            self.bot.unload_extension(module)
            self.bot.load_extension(module)
            await self.bot.say("I have just reloaded the {} module".format(module))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))


def setup(bot):
    bot.add_cog(Mod(bot))
