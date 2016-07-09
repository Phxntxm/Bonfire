from discord.ext import commands
from .utils import checks


class Mod:
    """Commands that can be used by a or an admin, depending on the command"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.isAdmin()
    async def leave(self, ctx):
        """Forces the bot to leave the server"""
        try:
            await self.bot.say('Why must I leave? Hopefully I can come back :c')
            await self.bot.leave_server(ctx.message.server)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))

    @commands.command(pass_context=True)
    @checks.isMod()
    async def say(self, ctx, *msg: str):
        """Tells the bot to repeat what you say"""
        try:
            msg = ' '.join(msg)
            await self.bot.say(msg)
            await self.bot.delete_message(ctx.message)
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))


def setup(bot):
    bot.add_cog(Mod(bot))
