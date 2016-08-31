from discord.ext import commands
import discord
from . import config


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
            required_perm_value = await config.get_content('custom_permissions')[ctx.message.server.id][
                ctx.command.qualified_name]
            required_perm = discord.Permissions(required_perm_value)
        except KeyError:
            required_perm = default_perms
        except TypeError:
            required_perm = default_perms
        return member_perms >= required_perm
    predicate.perms = perms
    return commands.check(predicate)


def is_pm():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
