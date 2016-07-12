from discord.ext import commands
from . import config


def isOwner():
    def predicate(ctx):
        return ctx.message.author.id == config.ownerID

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
