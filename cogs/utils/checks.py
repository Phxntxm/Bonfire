from discord.ext import commands
from . import config


def isOwner(ctx):
    return ctx.message.author.id == config.ownerID


def customPermsOrRole(perm):
    def predicate(ctx):
        if ctx.message.channel.is_private:
            return False
        custom_permissions = config.getContent('custom_permissions')
        try:
            _perm = custom_permissions[ctx.message.server.id][str(ctx.command)]
        except KeyError:
            pass
            
        if _perm is None:
            return getattr(ctx.message.author.permissions_in(ctx.message.channel), perm)
        else:
            return getattr(ctx.message.author.permissions_in(ctx.message.channel), _perm)

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
