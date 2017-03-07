import asyncio
import rethinkdb as r

from discord.ext import commands
import discord
from . import config

loop = asyncio.get_event_loop()

# The list of tables needed for the database
table_list = ['battle_records', 'battling', 'boops', 'bot_data', 'command_usage', 'custom_permissions',
              'deviantart', 'motd', 'nsfw_channels', 'overwatch', 'picarto', 'prefixes', 'raffles',
              'rules', 'server_alerts', 'strawpolls', 'tags', 'tictactoe', 'twitch', 'user_notifications']


async def db_check():
    """Used to check if the required database/tables are setup"""
    db_opts = config.db_opts

    r.set_loop_type('asyncio')
    # First try to connect, and see if the correct information was provided
    try:
        conn = await r.connect(**db_opts)
    except r.errors.ReqlDriverError:
        print("Cannot connect to the RethinkDB instance with the following information: {}".format(db_opts))

        print("The RethinkDB instance you have setup may be down, otherwise please ensure you setup a"
              " RethinkDB instance, and you have provided the correct database information in config.yml")
        quit()
        return

    # Get the current databases and check if the one we need is there
    dbs = await r.db_list().run(conn)
    if db_opts['db'] not in dbs:
        # If not, we want to create it
        print('Couldn\'t find database {}...creating now'.format(db_opts['db']))
        await r.db_create(db_opts['db']).run(conn)
        # Then add all the tables
        for table in table_list:
            print("Creating table {}...".format(table))
            await r.table_create(table).run(conn)
        print("Done!")
    else:
        # Otherwise, if the database is setup, make sure all the required tables are there
        tables = await r.table_list().run(conn)
        for table in table_list:
            if table not in tables:
                print("Creating table {}...".format(table))
                await r.table_create(table).run(conn)
        print("Done checking tables!")


def is_owner(ctx):
    return ctx.message.author.id in config.owner_ids


def custom_perms(**perms):
    def predicate(ctx):
        # Return true if this is a private channel, we'll handle that in the registering of the command
        if ctx.message.channel is discord.DMChannel:
            return True

        # Get the member permissions so that we can compare
        member_perms = ctx.message.author.permissions_in(ctx.message.channel)
        # Next, set the default permissions if one is not used, based on what was passed
        # This will be overriden later, if we have custom permissions
        required_perm = discord.Permissions.none()
        for perm, setting in perms.items():
            setattr(required_perm, perm, setting)

        perm_values = config.cache.get('custom_permissions').values

        # Loop through and find this server's entry for custom permissions
        # Find the command we're using, if it exists, then overwrite
        # The required permissions, based on the value saved
        for x in perm_values:
            if x['server_id'] == ctx.message.server.id and x.get(ctx.command.qualified_name):
                required_perm = discord.Permissions(x[ctx.command.qualified_name])

        # Now just check if the person running the command has these permissions
        return member_perms >= required_perm

    predicate.perms = perms
    return commands.check(predicate)
