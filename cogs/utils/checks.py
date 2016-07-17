from discord.ext import commands
from . import config


def isOwner(ctx):
    return ctx.message.author.id == config.ownerID


def customPermsOrRole(perm):
    def predicate(ctx):
        nonlocal perm
        if ctx.message.channel.is_private:
            return False
        custom_permissions = config.getContent('custom_permissions')
        try:
            perm = custom_permissions[ctx.message.server.id][str(ctx.command)]
        except KeyError:
            pass
        
        if perm == "none":
            return True
        return getattr(ctx.message.author.permissions_in(ctx.message.channel),perm)

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
