from discord.ext import commands
import discord
from . import config


def isOwner(ctx):
    return ctx.message.author.id == config.ownerID


def customPermsOrRole(**perms):
    def predicate(ctx):
        if ctx.message.channel.is_private:
            return False

        member_perms = ctx.message.author.permissions_in(ctx.message.channel)
        default_perms = discord.Permissions.none()
        for perm, setting in perms.items():
            setattr(default_perms, perm, setting)

        try:
            required_perm_value = config.getContent('custom_permissions')[ctx.message.server.id][
                ctx.command.qualified_name]
            required_perm = discord.Permissions(required_perm_value)
        except KeyError:
            required_perm = default_perms
        return member_perms >= required_perm

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
