import asyncio

from discord.ext import commands
import discord
from . import config

loop = asyncio.get_event_loop()


def is_owner(ctx):
    return ctx.message.author.id in config.owner_ids


def custom_perms(**perms):
    def predicate(ctx):
        # Return true if this is a private channel, we'll handle that in the registering of the command
        if ctx.message.channel.is_private:
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


def is_pm():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
