#!/usr/local/bin/python3.5

import discord
import traceback
import sys
from discord.ext import commands
from cogs.utils import config

extensions = ['cogs.interaction',
              'cogs.core',
              'cogs.mod',
              'cogs.owner',
              'cogs.stats',
              'cogs.playlist',
              'cogs.twitch',
              'cogs.overwatch']

bot = commands.Bot(command_prefix=config.commandPrefix, description=config.botDescription, pm_help=None)


# Bot event overrides
@bot.event
async def on_ready():
    # Change the status upon connection to the default status
    await bot.change_status(discord.Game(name=config.defaultStatus, type=0))
    channel_id = config.getContent('restart_server')
    if result != 0:
        destination = discord.utils.find(lambda m: m.id == result, bot.get_all_channels())
        await bot.send_message(destination, "I have just finished restarting!")
        config.saveContent('restart_server',0)


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
    await bot.send_message(member.server, "Welcome to the '{0.server.name}' server {0.mention}!".format(member))


@bot.event
async def on_member_remove(member):
    await bot.send_message(member.server, "{0} has left the server, I hope it wasn't because of something I said :c".format(member))


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.CommandNotFound):
        fmt = "That is not a valid command! There's a help command for a reason, learn to use it."
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.BadArgument):
        fmt = "Please provide a valid argument to pass to the command: {}".format(error)
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.CheckFailure):
        fmt = "You can't tell me what to do!"
        await bot.send_message(ctx.message.channel, fmt)
    #elif isinstance(error, commands.CommandInvokeError):
        #f = open("/home/phxntx5/public_html/Bonfire/error_log", 'w')
        #print('In {0.command.qualified_name}:'.format(ctx), file=f)
        #traceback.print_tb(error.original.__traceback__, file=f)
        #print('{0.__class__.__name__}: {0}'.format(error.original), file=f)
    else:
        fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
        await bot.send_message(ctx.message.channel, fmt.format(type(error).__name__, error))

if __name__ == '__main__':
    for e in extensions:
        bot.load_extension(e)
    bot.run(config.botToken)
