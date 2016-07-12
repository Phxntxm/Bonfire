from discord.ext import commands
from .utils import checks
from .utils import config
import pymysql


class Mod:
    """Commands that can be used by a or an admin, depending on the command"""
    def __init__(self, bot):
        self.bot = bot
    
    @commands.group(pass_context=True)
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed: {0.subcommand_passed}'.format(ctx))
            
    @nsfw.command(name="add", pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def nsfw_add(self, ctx):
        """Registers this channel as a 'nsfw' channel"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        try:
            cursor.execute('insert into nsfw_channels (channel_id) values ("{}")'.format(ctx.message.channel.id))
        except pymysql.IntegrityError:
            await self.bot.say("This channel is already registered as 'nsfw'!")
            config.closeConnection()
            return
        config.closeConnection()
        await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")
    
    @nsfw.command(name="remove", aliases=["delete"], pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from nsfw_channels where channel_id="{}"'.format(ctx.message.channel.id))
        if cursor.fetchone() is None:
            await self.bot.say("This channel is not registered as a ''nsfw' channel!")
            config.closeConnection()
            return

        cursor.execute('delete from nsfw_channels where channel_id="{}"'.format(ctx.message.channel.id))
        config.closeConnection()
        await self.bot.say("This channel has just been unregistered as a nsfw channel")
    
    @commands.command(pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def leave(self, ctx):
        """Forces the bot to leave the server"""
        await self.bot.say('Why must I leave? Hopefully I can come back :c')
        await self.bot.leave_server(ctx.message.server)

    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def say(self, ctx, *msg: str):
        """Tells the bot to repeat what you say"""
        msg = ' '.join(msg)
        await self.bot.say(msg)
        await self.bot.delete_message(ctx.message)


def setup(bot):
    bot.add_cog(Mod(bot))
