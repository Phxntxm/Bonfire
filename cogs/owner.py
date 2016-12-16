from discord.ext import commands

from .utils import config
from .utils import checks

import re
import glob
import discord
import inspect
import aiohttp
import pendulum
import asyncio

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(checks.is_owner)
    async def motd_push(self, *, message):
        """Used to push a new message to the message of the day"""
        date = pendulum.utcnow().to_date_string()
        r_filter = {'date': date}
        entry = {'motd': message, 'date': date}
        # Try to add this, if there's an entry for that date, lets update it to make sure only one motd is sent a day
        # I should be managing this myself, more than one should not be sent in a day
        if await config.add_content('motd', entry, r_filter):
            await config.update_content('motd', entry, r_filter)
        await self.bot.say("New motd update for {}!".format(date))

    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def debug(self, ctx):
        """Executes code"""
        # Eval and exec have different useful purposes, so use both
        try:

            # `Get all content in this format`
            match_single = getter.findall(ctx.message.content)
            # ```\nGet all content in this format```
            match_multi = multi.findall(ctx.message.content)

            if match_single:
                result = eval(match_single[0])

                # In case the result needs to be awaited, handle that
                if inspect.isawaitable(result):
                    result = await result
                await self.bot.say("```\n{0}```".format(result))
            elif match_multi:
                # Internal method to send the message to the channel, of whatever is passed
                def r(v):
                    self.bot.loop.create_task(self.bot.say("```\n{}```".format(v)))

                exec(match_multi[0])
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))

    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await self.bot.say(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.check(checks.is_owner)
    async def name(self, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await self.bot.say('Changed username to ' + newNick)

    @commands.command()
    @commands.check(checks.is_owner)
    async def status(self, *, status: str):
        """Changes the bot's 'playing' status"""
        await self.bot.change_status(discord.Game(name=status, type=0))
        await self.bot.say("Just changed my status to '{0}'!".format(status))

    @commands.command()
    @commands.check(checks.is_owner)
    async def load(self, *, module: str):
        """Loads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        # This try catch will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await self.bot.say("I have just loaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))

    @commands.command()
    @commands.check(checks.is_owner)
    async def unload(self, *, module: str):
        """Unloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        self.bot.unload_extension(module)
        await self.bot.say("I have just unloaded the {} module".format(module))

    @commands.command()
    @commands.check(checks.is_owner)
    async def reload(self, *, module: str):
        """Reloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)
        self.bot.unload_extension(module)

        # This try block will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await self.bot.say("I have just reloaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))


def setup(bot):
    bot.add_cog(Owner(bot))
