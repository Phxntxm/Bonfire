from discord.ext import commands
from . import config


def isOwner():
    def predicate(ctx):
        return ctx.message.author.id == config.ownerID

    return commands.check(predicate)


def isMod():
    def predicate(ctx):
        return ctx.message.author.top_role.permissions.kick_members

    return commands.check(predicate)


def isAdmin():
    def predicate(ctx):
        return ctx.message.author.top_role.permissions.manage_server

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)


def battled(battleP2=None):
    def predicate(ctx):
        return ctx.message.author == battleP2

    return commands.check(predicate)
