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


def get_syntax_error(e):
    if e.text is None:
        return '```py\n{0.__class__.__name__}: {0}\n```'.format(e)
    return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)


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

    async def on_guild_join(self, guild):
        # Create our embed that we'll use for the information
        embed = discord.Embed(title="Joined guild {}".format(guild.name), description="Created on: {}".format(guild.created_at.date()))

        # Make sure we only set the icon url if it has been set
        if guild.icon_url != "":
            embed.set_thumbnail(url=guild.icon_url)

        # Add our fields, these are self-explanatory
        embed.add_field(name='Region', value=str(guild.region))
        embed.add_field(name='Total Emojis', value=len(guild.emojis))

        # Get the amount of online members
        online_members = [m for m in guild.members if str(m.status) == 'online']
        embed.add_field(name='Total members', value='{}/{}'.format(len(online_members), guild.member_count))
        embed.add_field(name='Roles', value=len(guild.roles))

        # Split channels into voice and text channels
        voice_channels = [c for c in guild.channels if type(c) is discord.VoiceChannel]
        text_channels = [c for c in guild.channels if type(c) is discord.TextChannel]
        embed.add_field(name='Channels', value='{} text, {} voice'.format(len(text_channels), len(voice_channels)))
        embed.add_field(name='Owner', value=guild.owner.display_name)

        await self.bot.owner.send(embed=embed)

    async def on_guild_remove(self, guild):
        # Create our embed that we'll use for the information
        embed = discord.Embed(title="Left guild {}".format(guild.name), description="Created on: {}".format(guild.created_at.date()))

        # Make sure we only set the icon url if it has been set
        if guild.icon_url != "":
            embed.set_thumbnail(url=guild.icon_url)

        # Add our fields, these are self-explanatory
        embed.add_field(name='Region', value=str(guild.region))
        embed.add_field(name='Total Emojis', value=len(guild.emojis))

        # Get the amount of online members
        online_members = [m for m in guild.members if str(m.status) == 'online']
        embed.add_field(name='Total members', value='{}/{}'.format(len(online_members), guild.member_count))
        embed.add_field(name='Roles', value=len(guild.roles))

        # Split channels into voice and text channels
        voice_channels = [c for c in guild.channels if type(c) is discord.VoiceChannel]
        text_channels = [c for c in guild.channels if type(c) is discord.TextChannel]
        embed.add_field(name='Channels', value='{} text, {} voice'.format(len(text_channels), len(voice_channels)))
        embed.add_field(name='Owner', value=guild.owner.display_name)

        await self.bot.owner.send(embed=embed)


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
            'self': self,
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
                    await ctx.send(get_syntax_error(e))
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
    async def sendtochannel(self, ctx, cid: int, *, message):
        """Sends a message to a provided channel, by ID"""
        channel = self.bot.get_channel(cid)
        await channel.send(message)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    @commands.command()
    @commands.check(utils.is_owner)
    async def debug(self, ctx, *, body: str):
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.message.channel,
            'author': ctx.message.author,
            'server': ctx.message.guild,
            'guild': ctx.message.guild,
            'message': ctx.message,
            'self': self,
            '_': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = 'async def func():\n%s' % textwrap.indent(body, '  ')

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return await ctx.send(get_syntax_error(e))

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send('```py\n{}{}\n```'.format(value, traceback.format_exc()))
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            try:
                if ret is None:
                    if value:
                        await ctx.send('```py\n%s\n```' % value)
                else:
                    self._last_result = ret
                    await ctx.send('```py\n%s%s\n```' % (value, ret))
            except discord.HTTPException:
                await ctx.send("Content too large for me to print!")

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
