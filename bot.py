#!/usr/local/bin/python3.5

import discord
from discord.ext import commands
from cogs.utils import config

extensions = ['cogs.interaction',
              'cogs.core',
              'cogs.mod',
              'cogs.owner',
              'cogs.stats',
              'cogs.playlist']

bot = commands.Bot(command_prefix=config.commandPrefix, description=config.botDescription, pm_help="True")


# Bot event overrides
@bot.event
async def on_ready():
    # Change the status upon connection to the default status
    game = discord.Game(name=config.defaultStatus, type=0)
    await bot.change_status(game)
    cursor = config.connection.cursor()

    cursor.execute('use {0}'.format(config.db_default))
    cursor.execute('select channel_id from restart_server where id=1')
    result = cursor.fetchone()['channel_id']
    if int(result) != 0:
        destination = discord.utils.find(lambda m: m.id == result, bot.get_all_channels())
        await bot.send_message(destination, "I have just finished restarting!")
        cursor.execute('update restart_server set channel_id=0 where id=1')
        config.connection.commit()


@bot.event
async def on_member_join(member):
    await bot.say("Welcome to the '{0.server.name}' server {0.mention}!".format(member))


@bot.event
async def on_member_remove(member):
    await bot.say("{0} has left the server, I hope it wasn't because of something I said :c".format(member))


@bot.event
async def on_command_error(error, ctx):
    fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
    await bot.say(fmt.format(type(e).__name__, e))

if __name__ == '__main__':
    for e in extensions:
        bot.load_extension(e)
    bot.run(config.botToken)
