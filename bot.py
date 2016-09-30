#!/usr/local/bin/python3.5
import discord
import traceback
import logging
import datetime
import pendulum
import os

os.chdir(os.path.dirname(os.path.realpath(__file__)))

from discord.ext import commands
from cogs.utils import config

extensions = ['cogs.interaction',
              'cogs.core',
              'cogs.mod',
              'cogs.owner',
              'cogs.stats',
              'cogs.playlist',
              'cogs.twitch',
              'cogs.picarto',
              'cogs.overwatch',
              'cogs.links',
              'cogs.tags',
              'cogs.roles',
              'cogs.strawpoll',
              'cogs.tictactoe',
              'cogs.hangman',
              'cogs.statsupdate']

opts = {'command_prefix': config.command_prefix,
        'description': config.bot_description,
        'pm_help': None,
        'shard_count': config.shard_count,
        'shard_id': config.shard_id}

bot = commands.Bot(**opts)
logging.basicConfig(level=logging.INFO, filename='bonfire.log')


@bot.event
async def on_ready():
    # Change the status upon connection to the default status
    await bot.change_status(discord.Game(name=config.default_status, type=0))

    if not hasattr(bot, 'uptime'):
        bot.uptime = pendulum.utcnow()


@bot.event
async def on_member_join(member):
    r_filter = {'server_id': member.server.id}
    notifications = await config.get_content('user_notifications', r_filter)
    try:
        channel_id = notifications[0]['channel_id']
    except TypeError:
        return

    # By default, notifications should be off unless explicitly turned on
    if not channel_id:
        return

    channel = discord.utils.get(member.server.channels, id=notifications)
    await bot.send_message(channel, "Welcome to the '{0.server.name}' server {0.mention}!".format(member))


@bot.event
async def on_member_remove(member):
    r_filter = {'server_id': member.server.id}
    notifications = await config.get_content('user_notifications', r_filter)
    try:
        channel_id = notifications[0]['channel_id']
    except TypeError:
        return

    # By default, notifications should be off unless explicitly turned on
    if not channel_id:
        return

    channel = discord.utils.get(member.server.channels, id=channel_id)
    await bot.send_message(channel,
                           "{0} has left the server, I hope it wasn't because of something I said :c".format(
                               member.display_name))


@bot.event
async def on_message(message):
    if message.author.bot:
        return
    await bot.process_commands(message)


@bot.event
async def on_command_completion(command, ctx):
    # There's no reason to continue waiting for this to complete, so lets immediately launch this in a new future
    bot.loop.create_task(process_command(command, ctx))
    now = datetime.datetime.now()

    fmt = "In server '{0.message.server}' at {1}\n" \
          "Full message: `{0.message.content}`\n" \
          "Command detected was: {}\n" \
          "ctx command would be: {0.command.qualified_name}\n\n".format(
           ctx, str(now), command.qualified_name)
    with open('command_log', 'a') as l:
        print(fmt, file=l)


async def process_command(command, ctx):
    # This try catch is only here while this is first being implemented
    # It will be removed once I ensure this is working correctly
    author = ctx.message.author
    server = ctx.message.server

    r_filter = {'command': command.qualified_name}
    command_usage = await config.get_content('command_usage', r_filter)
    if command_usage is None:
        command_usage = {'command': command.qualified_name}
    else:
        command_usage = command_usage[0]
    # Add one to the total usage for this command, basing it off 0 to start with (obviously)
    total_usage = command_usage.get('total_usage', 0) + 1
    command_usage['total_usage'] = total_usage

    # Add one to the author's usage for this command
    total_member_usage = command_usage.get('member_usage', {})
    member_usage = total_member_usage.get(author.id, 0) + 1
    total_member_usage[author.id] = member_usage
    command_usage['member_usage'] = total_member_usage

    # Add one to the server's usage for this command
    total_server_usage = command_usage.get('server_usage', {})
    server_usage = total_server_usage.get(server.id, 0) + 1
    total_server_usage[server.id] = server_usage
    command_usage['server_usage'] = total_server_usage

    # Save all the changes
    if not await config.update_content('command_usage', command_usage, r_filter):
        await config.add_content('command_usage', command_usage, r_filter)


@bot.event
async def on_command_error(error, ctx):
    if isinstance(error, commands.CommandNotFound):
        return
    try:
        if isinstance(error.original, discord.Forbidden):
            return
    except AttributeError:
        pass

    if isinstance(error, commands.BadArgument):
        fmt = "Please provide a valid argument to pass to the command: {}".format(error)
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.CheckFailure):
        fmt = "You can't tell me what to do!"
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.CommandOnCooldown):
        m, s = divmod(error.retry_after, 60)
        fmt = "This command is on cooldown! Hold your horses! >:c\nTry again in {} minutes and {} seconds" \
            .format(round(m), round(s))
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.NoPrivateMessage):
        fmt = "This command cannot be used in a private message"
        await bot.send_message(ctx.message.channel, fmt)
    elif isinstance(error, commands.MissingRequiredArgument):
        await bot.send_message(ctx.message.channel, error)
    else:
        now = datetime.datetime.now()
        with open("error_log", 'a') as f:
            print("In server '{0.message.server}' at {1}\nFull command: `{0.message.content}`".format(ctx, str(now)),
                  file=f)
            try:
                traceback.print_tb(error.original.__traceback__, file=f)
                print('{0.__class__.__name__}: {0}'.format(error.original), file=f)
            except:
                traceback.print_tb(error.__traceback__, file=f)
                print('{0.__class__.__name__}: {0}'.format(error), file=f)


if __name__ == '__main__':
    for e in extensions:
        bot.load_extension(e)
    bot.run(config.bot_token)
