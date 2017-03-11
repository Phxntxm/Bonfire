import asyncio
import rethinkdb as r

from discord.ext import commands
import discord
from . import config

loop = asyncio.get_event_loop()

# The tables needed for the database, as well as their primary keys
required_tables = {
    'battle_records': 'member_id',
    'boops': 'member_id',
    'command_usage': 'command',
    'deviantart': 'member_id',
    'motd': 'date',
    'overwatch': 'member_id',
    'picarto': 'member_id',
    'server_settings': 'server_id',
    'raffles': 'id',
    'strawpolls': 'server_id',
    'osu': 'member_id',
    'tags': 'server_id',
    'tictactoe': 'member_id',
    'twitch': 'member_id'
}


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
        for table, key in required_tables.items():
            print("Creating table {}...".format(table))
            await r.table_create(table, primary_key=key).run(conn)
        print("Done!")
    else:
        # Otherwise, if the database is setup, make sure all the required tables are there
        tables = await r.table_list().run(conn)
        for table, key in required_tables.items():
            if table not in tables:
                print("Creating table {}...".format(table))
                await r.table_create(table, primary_key=key).run(conn)
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

        try:
            server_settings = config.cache.get('server_settings').values
            required_perm_value = [x for x in server_settings if x['server_id'] == str(
                ctx.message.guild.id)][0]['permissions'][ctx.command.qualified_name]
            required_perm = discord.Permissions(required_perm_value)
        except (TypeError, IndexError, KeyError):
            pass

        # Now just check if the person running the command has these permissions
        return member_perms >= required_perm

    predicate.perms = perms
    return commands.check(predicate)
