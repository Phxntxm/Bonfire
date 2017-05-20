#!/usr/local/bin/python3.5
import discord
import traceback
import logging
import datetime
import pendulum
import os
import aiohttp

os.chdir(os.path.dirname(os.path.realpath(__file__)))

from discord.ext import commands
from cogs import utils

opts = {'command_prefix': utils.command_prefix,
        'description': utils.bot_description,
        'pm_help': None,
        'command_not_found': '',
        'game': discord.Game(name=utils.default_status, type=0)}

bot = commands.AutoShardedBot(**opts)
logging.basicConfig(level=logging.INFO, filename='bonfire.log')


@bot.event
async def on_ready():
    if not hasattr(bot, 'uptime'):
        bot.uptime = pendulum.utcnow()
    if not hasattr(bot, 'owner'):
        appinfo = await bot.application_info()
        bot.owner = appinfo.owner


@bot.event
async def on_message(message):
    if message.author.bot or utils.should_ignore(message):
        return
    await bot.process_commands(message)


@bot.event
async def on_command_completion(ctx):
    # There's no reason to continue waiting for this to complete, so lets immediately launch this in a new future
    bot.loop.create_task(process_command(ctx))


async def process_command(ctx):
    author = ctx.message.author
    server = ctx.message.guild
    command = ctx.command

    command_usage = await utils.get_content('command_usage', key=command.qualified_name)
    if command_usage is None:
        command_usage = {'command': command.qualified_name}

    # Add one to the total usage for this command, basing it off 0 to start with (obviously)
    total_usage = command_usage.get('total_usage', 0) + 1
    command_usage['total_usage'] = total_usage

    # Add one to the author's usage for this command
    total_member_usage = command_usage.get('member_usage', {})
    member_usage = total_member_usage.get(str(author.id), 0) + 1
    total_member_usage[str(author.id)] = member_usage
    command_usage['member_usage'] = total_member_usage

    # Add one to the server's usage for this command
    if ctx.message.guild is not None:
        total_server_usage = command_usage.get('server_usage', {})
        server_usage = total_server_usage.get(str(server.id), 0) + 1
        total_server_usage[str(server.id)] = server_usage
        command_usage['server_usage'] = total_server_usage

    # Save all the changes
    if not await utils.update_content('command_usage', command_usage, command.qualified_name):
        await utils.add_content('command_usage', command_usage)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.DisabledCommand):
        return
    try:
        if isinstance(error.original, discord.Forbidden):
            return
        elif isinstance(error.original, discord.HTTPException) and 'empty message' in str(error.original):
            return
        elif isinstance(error.original, aiohttp.ClientOSError):
            return
    except AttributeError:
        pass

    try:
        if isinstance(error, commands.BadArgument):
            fmt = "Please provide a valid argument to pass to the command: {}".format(error)
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.CheckFailure):
            fmt = "You can't tell me what to do!"
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.CommandOnCooldown):
            m, s = divmod(error.retry_after, 60)
            fmt = "This command is on cooldown! Hold your horses! >:c\nTry again in {} minutes and {} seconds" \
                .format(round(m), round(s))
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.NoPrivateMessage):
            fmt = "This command cannot be used in a private message"
            await ctx.message.channel.send(fmt)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.message.channel.send(error)
        else:
            now = datetime.datetime.now()
            with open("error_log", 'a') as f:
                print("In server '{0.message.guild}' at {1}\nFull command: `{0.message.content}`".format(ctx, str(now)),
                      file=f)
                try:
                    traceback.print_tb(error.original.__traceback__, file=f)
                    print('{0.__class__.__name__}: {0}'.format(error.original), file=f)
                except:
                    traceback.print_tb(error.__traceback__, file=f)
                    print('{0.__class__.__name__}: {0}'.format(error), file=f)
    except discord.HTTPException:
        pass


if __name__ == '__main__':
    bot.loop.create_task(utils.db_check())
    bot.remove_command('help')

    for e in utils.extensions:
        bot.load_extension(e)
    bot.run(utils.bot_token)
