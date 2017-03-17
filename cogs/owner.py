from discord.ext import commands

from . import utils

import re
import glob
import discord
import inspect
import aiohttp
import pendulum
import asyncio


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(utils.is_owner)
    async def motd_push(self, *, message):
        """Used to push a new message to the message of the day"""
        date = pendulum.utcnow().to_date_string()
        key = date
        entry = {'motd': message, 'date': date}
        # Try to add this, if there's an entry for that date, lets update it to make sure only one motd is sent a day
        # I should be managing this myself, more than one should not be sent in a day
        if await utils.add_content('motd', entry):
            await utils.update_content('motd', entry, key)
        await self.bot.say("New motd update for {}!".format(date))

    @commands.command(pass_context=True)
    @commands.check(utils.is_owner)
    async def debug(self, ctx, *, code : str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'
        result = None

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'server': ctx.message.server,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await self.bot.say(python.format(type(e).__name__ + ': ' + str(e)))
            return
        try:
            await self.bot.say(python.format(result))
        except discord.HTTPException:
            await self.bot.say("Result is too long for me to send")
        except:
            pass

    @commands.command(pass_context=True)
    @commands.check(utils.is_owner)
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await self.bot.say(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.check(utils.is_owner)
    async def name(self, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await self.bot.say('Changed username to ' + newNick)

    @commands.command()
    @commands.check(utils.is_owner)
    async def status(self, *, status: str):
        """Changes the bot's 'playing' status"""
        await self.bot.change_status(discord.Game(name=status, type=0))
        await self.bot.say("Just changed my status to '{0}'!".format(status))

    @commands.command()
    @commands.check(utils.is_owner)
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
    @commands.check(utils.is_owner)
    async def unload(self, *, module: str):
        """Unloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        self.bot.unload_extension(module)
        await self.bot.say("I have just unloaded the {} module".format(module))

    @commands.command()
    @commands.check(utils.is_owner)
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
