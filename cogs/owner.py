from discord.ext import commands

from . import utils

import re
import glob
import asyncio
import aiohttp
import discord
import inspect
import pendulum
import textwrap
import traceback
from contextlib import redirect_stdout
import io


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot
        self._last_result = None
        self.sessions = set()

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    def get_syntax_error(self, e):
        return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)

    @commands.command(hidden=True)
    @commands.check(utils.is_owner)
    async def repl(self, ctx):
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'guild': msg.guild,
            'server': msg.guild,
            'channel': msg.channel,
            'author': msg.author,
            '_': None,
        }

        if msg.channel.id in self.sessions:
            await ctx.send('Already running a REPL session in this channel. Exit it with `quit`.')
            return

        self.sessions.add(msg.channel.id)
        await ctx.send('Enter code to execute or evaluate. `exit()` or `quit` to exit.')

        def check(m):
            return m.author.id == msg.author.id and \
                   m.channel.id == msg.channel.id and \
                   m.content.startswith('`')

        while True:
            try:
                response = await self.bot.wait_for('message', check=check, timeout=10.0 * 60.0)
            except asyncio.TimeoutError:
                await ctx.send('Exiting REPL session.')
                self.sessions.remove(msg.channel.id)
                break

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await ctx.send('Exiting.')
                self.sessions.remove(msg.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await ctx.send(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = '```py\n{}{}\n```'.format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = '```py\n{}{}\n```'.format(value, result)
                    variables['_'] = result
                elif value:
                    fmt = '```py\n{}\n```'.format(value)

            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await ctx.send('Content too big to be printed.')
                    else:
                        await ctx.send(fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send('Unexpected error: `{}`'.format(e))

    @commands.command()
    @commands.check(utils.is_owner)
    async def motd_push(self, ctx, *, message):
        """Used to push a new message to the message of the day"""
        date = pendulum.utcnow().to_date_string()
        key = date
        entry = {'motd': message, 'date': date}
        # Try to add this, if there's an entry for that date, lets update it to make sure only one motd is sent a day
        # I should be managing this myself, more than one should not be sent in a day
        if await utils.add_content('motd', entry):
            await utils.update_content('motd', entry, key)
        await ctx.send("New motd update for {}!".format(date))

    @commands.command()
    @commands.check(utils.is_owner)
    async def sendtochannel(self, ctx, cid, message):
        """Sends a message to a provided channel, by ID"""
        channel = self.bot.get_channel(cid)
        await channel.send(message)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

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
    async def name(self, ctx, new_nick: str):
        """Changes the bot's name"""
        await self.bot.user.edit(username=new_nick)
        await ctx.send('Changed username to ' + new_nick)

    @commands.command()
    @commands.check(utils.is_owner)
    async def status(self, ctx, *, status: str):
        """Changes the bot's 'playing' status"""
        await self.bot.change_presence(game=discord.Game(name=status, type=0))
        await ctx.send("Just changed my status to '{}'!".format(status))

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
