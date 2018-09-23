import asyncio
import rethinkdb as r

from discord.ext import commands
import discord
from . import config
from . import utilities

loop = asyncio.get_event_loop()

# The tables needed for the database, as well as their primary keys
required_tables = {
    'battle_records': 'member_id',
    'boops': 'member_id',
    'command_usage': 'command',
    'overwatch': 'member_id',
    'picarto': 'member_id',
    'server_settings': 'server_id',
    'raffles': 'server_id',
    'strawpolls': 'server_id',
    'osu': 'member_id',
    'tags': 'server_id',
    'tictactoe': 'member_id',
    'twitch': 'member_id',
    'user_playlists': 'member_id',
    'birthdays': 'member_id'
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
    if not hasattr(ctx.bot, "owner"):
        return False
    return ctx.bot.owner.id == ctx.message.author.id


def should_ignore(ctx):
    if ctx.message.guild is None:
        return False
    ignored = ctx.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='ignored')
    if not ignored:
        return False
    return str(ctx.message.author.id) in ignored['members'] or str(ctx.message.channel.id) in ignored['channels']


async def check_restricted(ctx):
    # Return true if this is a private channel, we'll handle that in the registering of the command
    if type(ctx.message.channel) is discord.DMChannel:
        return True

    # First get all the restrictions
    restrictions = ctx.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='restrictions') or {}
    # Now lets check the "from" restrictions
    for from_restriction in restrictions.get('from', []):
        # Get the source and destination
        # Source should ALWAYS be a command in this case
        source = from_restriction.get('source')
        destination = from_restriction.get('destination')
        # Convert destination to the object we want
        destination = await utilities.convert(ctx, destination)
        # If we couldn't find the destination, just continue with other restrictions
        # Also if this restriction we're checking isn't for this command
        if destination is None or source != ctx.command.qualified_name:
            continue

        # This means that the type of restriction we have is `command from channel`
        # Which means we do not want commands to be ran in this channel
        if destination == ctx.message.channel:
            return False
        # This type is `command from Role` meaning anyone with this role can't run this command
        elif destination in ctx.message.author.roles:
            return False
        # This is `command from Member` meaning this user specifically cannot run this command
        elif destination == ctx.message.author:
            return False

    # If we are here, then there are no blacklists stopping this from running

    # Now for the to restrictions this is a little different, we need to make a whitelist and
    # see if our current channel is in this whitelist, as well as any whitelisted roles are in the author's roles
    # Only if there is no whitelist, do we want to blanket return True
    to_restrictions = restrictions.get('to', [])
    if len(to_restrictions) == 0:
        return True

    # Otherwise there is a whitelist, and we need to start it
    whitelisted_channels = []
    whitelisted_roles = []

    for to_restriction in to_restrictions:
        # Get the source and destination
        # Source should ALWAYS be a command in this case
        source = to_restriction.get('source')
        destination = to_restriction.get('destination')
        # Convert destination to the object we want
        destination = await utilities.convert(ctx, destination)
        # If we couldn't find the destination, just continue with other restrictions
        # Also if this restriction we're checking isn't for this command
        if destination is None or source != ctx.command.qualified_name:
            continue

        # Append to our two whitelists depending on what type this is
        if isinstance(destination, discord.TextChannel):
            whitelisted_channels.append(destination)
        elif isinstance(destination, discord.Role):
            whitelisted_roles.append(destination)

    if whitelisted_channels:
        if ctx.channel not in whitelisted_channels:
            return False
    if whitelisted_roles:
        if not any(x in ctx.message.author.roles for x in whitelisted_roles):
            return False

    # If we have passed all of these, then we are allowed to run this command
    # This looks like a whole lot, but all of these lists will be very tiny in almost all cases
    # And only delving deep into the specific lists that may be large, will we finally see "large" lists
    # Which means this still will not be slow in other cases
    return True


def has_perms(ctx, **perms):
    # Return true if this is a private channel, we'll handle that in the registering of the command
    if type(ctx.message.channel) is discord.DMChannel:
        return True

    # Get the member permissions so that we can compare
    guild_perms = ctx.message.author.guild_permissions
    channel_perms = ctx.message.author.permissions_in(ctx.message.channel)
    # Currently the library doesn't handle administrator overrides..so lets do this manually
    if guild_perms.administrator:
        return True
    # Next, set the default permissions if one is not used, based on what was passed
    # This will be overriden later, if we have custom permissions
    required_perm = discord.Permissions.none()
    for perm, setting in perms.items():
        setattr(required_perm, perm, setting)

    required_perm_value = ctx.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='permissions') or {}
    required_perm_value = required_perm_value.get(ctx.command.qualified_name)
    if required_perm_value:
        required_perm = discord.Permissions(required_perm_value)

    # Now just check if the person running the command has these permissions
    return guild_perms >= required_perm or channel_perms >= required_perm


def can_run(**kwargs):
    async def predicate(ctx):
        # First check if the command requires ownership of the bot
        if kwargs.pop("ownership", False) and not is_owner(ctx):
            return False
        # Next check if it requires any certain permissions
        if kwargs and not has_perms(ctx, **kwargs):
            return False
        # Next...check custom restrictions
        if await check_restricted(ctx):
            return False
        # Then if the user/channel should be ignored
        if should_ignore(ctx):
            return False
        # Otherwise....we're good
        return True

    predicate.perms = kwargs
    return commands.check(predicate)
