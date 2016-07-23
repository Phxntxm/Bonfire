from discord.ext import commands
from .utils import config
from .utils import checks
import urllib.request
import re
import os
import glob
import sys
import discord
import inspect
import aiohttp

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    @commands.check(checks.isOwner)
    async def restart(self, ctx):
        """Forces the bot to restart"""
        if config.saveContent('restart_server', ctx.message.channel.id):
            await self.bot.say("Restarting; see you in the next life {0}!".format(ctx.message.author.mention))
        else:
            await self.bot.say("I was unable to save this data")
        python = sys.executable
        os.execl(python, python, *sys.argv)

    @commands.command()
    @commands.check(checks.isOwner)
    async def adddoggo(self, url: str):
        """Saves a URL as an image to add for the doggo command"""
        os.chdir('/home/phxntx5/public_html/Bonfire/images')
        local_path = 'doggo{}.jpg'.format(len(glob.glob('doggo*')))
        with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                val = await r.read()
                with open(local_path, "wb") as f:
                    f.write(val)
        await self.bot.say(
            "Just saved a new doggo image! You now have {} doggo images!".format(len(glob.glob('doggo*'))))

    @commands.command(pass_context=True)
    @commands.check(checks.isOwner)
    async def debug(self, ctx):
        """Executes code"""
        match_single = getter.findall(ctx.message.content)
        match_multi = multi.findall(ctx.message.content)
        if not match_single and not match_multi:
            return
        else:
            if not match_multi:
                result = eval(match_single[0])

                if inspect.isawaitable(result):
                    result = await result
                await self.bot.say("```{0}```".format(result))
            else:
                def r(v):
                    config.loop.create_task(self.bot.say("```{0}```".format(v)))

                exec(match_multi[0])

    @commands.command(pass_context=True)
    @commands.check(checks.isOwner)
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await self.bot.say(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.check(checks.isOwner)
    async def avatar(self, content: str):
        """Changes the avatar for the bot to the filename following the command"""
        file = '/home/phxntx5/public_html/bot/images/' + content
        with open(file, 'rb') as fp:
            await self.bot.edit_profile(avatar=fp.read())

    @commands.command()
    @commands.check(checks.isOwner)
    async def name(self, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await self.bot.say('Changed username to ' + newNick)
        # Restart the bot after this, as profile changes are not immediate
        python = sys.executable
        os.execl(python, python, *sys.argv)

    @commands.command()
    @commands.check(checks.isOwner)
    async def status(self, *stat: str):
        """Changes the bot's 'playing' status"""
        newStatus = ' '.join(stat)
        game = discord.Game(name=newStatus, type=0)
        await self.bot.change_status(game)
        await self.bot.say("Just changed my status to '{0}'!".format(newStatus))

    @commands.command()
    @commands.check(checks.isOwner)
    async def load(self, *, module: str):
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
    @commands.check(checks.isOwner)
    async def unload(self, *, module: str):
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
    @commands.check(checks.isOwner)
    async def reload(self, *, module: str):
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
    bot.add_cog(Owner(bot))
