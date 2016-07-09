from discord.ext import commands
from .utils import config
from .utils import checks
import re
import os
import sys
import discord

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @checks.isOwner()
    async def restart(self, ctx):
        """Forces the bot to restart"""
            cursor = config.connection.cursor()
            cursor.execute('use {0}'.format(config.db_default))
            sql = "update restart_server set channel_id={0} where id=1".format(ctx.message.channel.id)
            cursor.execute(sql)
            config.connection.commit()
            await self.bot.say("Restarting; see you in the next life {0}!".format(ctx.message.author.mention))
            python = sys.executable
            os.execl(python, python, *sys.argv)

    @commands.command(pass_context=True)
    @checks.isOwner()
    async def py(self, ctx):
        """Executes code"""
        match_single = getter.findall(ctx.message.content)
        match_multi = multi.findall(ctx.message.content)
        if not match_single and not match_multi:
            return
        else:
            if not match_multi:
                result = eval(match_single[0])
                await self.bot.say("```{0}```".format(result))
            else:
                def r(v):
                    config.loop.create_task(self.bot.say("```{0}```".format(v)))

                exec(match_multi[0])

    @commands.command(pass_context=True)
    @checks.isOwner()
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await self.bot.say(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @checks.isOwner()
    async def avatar(self, content: str):
        """Changes the avatar for the bot to the filename following the command"""
        file = '/home/phxntx5/public_html/bot/images/' + content
        with open(file, 'rb') as fp:
            await self.bot.edit_profile(avatar=fp.read())

    @commands.command()
    @checks.isOwner()
    async def name(self, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await self.bot.say('Changed username to ' + newNick)
        # Restart the bot after this, as profile changes are not immediate
        python = sys.executable
        os.execl(python, python, *sys.argv)

    @commands.command()
    @checks.isOwner()
    async def status(self, *stat: str):
        """Changes the bot's 'playing' status"""
        newStatus = ' '.join(stat)
        game = discord.Game(name=newStatus, type=0)
        await self.bot.change_status(game)
        await self.bot.say("Just changed my status to '{0}'!".format(newStatus))


def setup(bot):
    bot.add_cog(Owner(bot))
