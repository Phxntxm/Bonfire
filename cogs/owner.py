from discord.ext import commands

from . import utils

import re
import glob
import asyncio
import aiohttp
import discord
import inspect
import pendulum


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(utils.is_owner)
    async def motd_push(self, ctx, *, message):
        """Used to push a new message to the message of the day"""
        date = pendulum.utcnow().to_date_string()
        r_filter = {'date': date}
        entry = {'motd': message, 'date': date}
        # Try to add this, if there's an entry for that date, lets update it to make sure only one motd is sent a day
        # I should be managing this myself, more than one should not be sent in a day
        if await utils.add_content('motd', entry, r_filter):
            await utils.update_content('motd', entry, r_filter)
        await ctx.send("New motd update for {}!".format(date))

    @commands.command()
    @commands.check(utils.is_owner)
    async def debug(self, ctx, *, code: str):
        """Evaluates code."""
        code = code.strip('` ')
        python = '```py\n{}\n```'

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'message': ctx.message,
            'server': ctx.message.guild,
            'channel': ctx.message.channel,
            'author': ctx.message.author
        }

        env.update(globals())

        try:
            result = eval(code, env)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            await ctx.send(python.format(type(e).__name__ + ': ' + str(e)))
            return
        try:
            await ctx.send(python.format(result))
        except discord.HTTPException:
            await ctx.send("Result is too long for me to send")
        except:
            pass

    @commands.command()
    @commands.check(utils.is_owner)
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await ctx.send(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.check(utils.is_owner)
    async def name(self, ctx, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await ctx.send('Changed username to ' + newNick)

    @commands.command()
    @commands.check(utils.is_owner)
    async def status(self, ctx, *, status: str):
        """Changes the bot's 'playing' status"""
        await self.bot.change_status(discord.Game(name=status, type=0))
        await ctx.send("Just changed my status to '{0}'!".format(status))

    @commands.command()
    @commands.check(utils.is_owner)
    async def load(self, ctx, *, module: str):
        """Loads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        # This try catch will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await ctx.send("I have just loaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await ctx.send(fmt.format(type(error).__name__, error))

    @commands.command()
    @commands.check(utils.is_owner)
    async def unload(self, ctx, *, module: str):
        """Unloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        self.bot.unload_extension(module)
        await ctx.send("I have just unloaded the {} module".format(module))

    @commands.command()
    @commands.check(utils.is_owner)
    async def reload(self, ctx, *, module: str):
        """Reloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)
        self.bot.unload_extension(module)

        # This try block will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await ctx.send("I have just reloaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await ctx.send(fmt.format(type(error).__name__, error))


def setup(bot):
    bot.add_cog(Owner(bot))
