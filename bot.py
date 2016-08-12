#!/usr/local/bin/python3.5

import discord
import traceback
import logging
import datetime
import os
import pendulum
from discord.ext import commands
from cogs.utils import config
from cogs.utils.config import getPhrase

os.chdir(os.path.dirname(os.path.realpath(__file__)))

extensions = ['cogs.interaction',
              'cogs.core',
              'cogs.mod',
              'cogs.owner',
              'cogs.stats',
              'cogs.playlist',
              'cogs.picarto',
              'cogs.twitch',
              'cogs.links',
              'cogs.tags',
              'cogs.roles',
              'cogs.statsupdate']

bot = commands.Bot(command_prefix=config.commandPrefix, description=config.botDescription, pm_help=None)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)

log = logging.getLogger()
log.setLevel(logging.INFO)
handler = logging.FileHandler(filename='bot.log', encoding='utf-8', mode='a')
log.addHandler(handler)


# Bot event overrides
@bot.event
async def on_ready():
    # Change the status upon connection to the default status
    await bot.change_status(discord.Game(name=config.defaultStatus, type=0))
    channel_id = config.getContent('restart_server')
    config.saveContent('battling',{})
    if channel_id != 0:
        destination = discord.utils.find(lambda m: m.id == channel_id, bot.get_all_channels())
        await bot.send_message(destination, getPhrase("RESTART_COMPLETE"))
        config.saveContent('restart_server', 0)
    if not hasattr(bot, 'uptime'):
        bot.uptime = pendulum.utcnow()


@bot.event
async def on_member_join(member):
    notifications = config.getContent('user_notifications') or {}
    server_notifications = notifications.get(member.server.id)
    if not server_notifications:
        return

    channel = discord.utils.get(member.server.channels, id=server_notifications)
    await bot.send_message(channel, getPhrase("MEMBER_JOIN").format(member.server.name, member.mention))


@bot.event
async def on_member_remove(member):
    notifications = config.getContent('user_notifications') or {}
    server_notifications = notifications.get(member.server.id)
    if not server_notifications:
        return

    channel = discord.utils.get(member.server.channels, id=server_notifications)
    await bot.send_message(channel,
                           getPhrase("MEMBER_LEAVE").format(
                               member.display_name))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.BadArgument):
        fmt = getPhrase("ERROR_BAD_ARGUMENT").format(error)
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.CheckFailure):
        fmt = getPhrase("ERROR_NO_PERMISSIONS")
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        fmt = getPhrase("ERROR_COOLDOWN").format(round(m), round(s))
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.NoPrivateMessage):
        fmt = getPhrase("ERROR_NOPM")
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.MissingRequiredArgument):
        await bot.send_message(ctx.message.channel, error)
    elif not isinstance(error, commands.CommandNotFound):
        now = datetime.datetime.now()
        with open("error.log", 'a') as f:
            print("In server '{0.message.server}' at {1}\nFull command: `{0.message.content}`".format(ctx, str(now)),
                  file=f)
            try:
                traceback.print_tb(error.original.__traceback__, file=f)
                print('{0.__class__.__name__}: {0}'.format(error.original), file=f)
            except:
                traceback.print_tb(error.__traceback__, file=f)
                print('{0.__class__.__name__}: {0}'.format(error), file=f)
        fmt = getPhrase("ERROR_INTERNAL").format(discord.utils.get(ctx.message.server.members, id=config.owner_ids))
        await bot.send_message(ctx.message.channel, fmt)


if __name__ == '__main__':
    for e in extensions:
        bot.load_extension(e)
    bot.run(config.botToken)
