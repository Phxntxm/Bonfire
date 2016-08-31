import asyncio

from discord.ext import commands
import discord
from . import config

loop = asyncio.get_event_loop()


def is_owner(ctx):
    return ctx.message.author.id in config.owner_ids


def custom_perms(**perms):
    def predicate(ctx):
        if ctx.message.channel.is_private:
            return False

        member_perms = ctx.message.author.permissions_in(ctx.message.channel)
        default_perms = discord.Permissions.none()
        for perm, setting in perms.items():
            setattr(default_perms, perm, setting)

        try:
            perm_values = config.cache.get('custom_permissions')
            required_perm_value = perm_values[ctx.message.server.id][ctx.command.qualified_name]
            required_perm = discord.Permissions(required_perm_value)
        except (KeyError, TypeError):
            required_perm = default_perms
        return member_perms >= required_perm

    predicate.perms = perms
    return commands.check(predicate)


def is_pm():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
