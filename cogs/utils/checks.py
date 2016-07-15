from discord.ext import commands
from . import config


def isOwner(ctx):
    return ctx.message.author.id == config.ownerID

def customPermsOrRole(perm):
    def predicate(ctx):
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_perms))
        cmd = str(ctx.command)
        sid = ctx.message.server.id
        
        cursor.execute("show tables like '{}'".format(sid))
        result = cursor.fetchone()
        config.closeConnection()
        if result is not None:
            if perm is None:
                return True
            else:
                for role in ctx.message.author.roles:
                    if getattr(role,perm):
                        return True:
                return False
        return True
    return commands.check(predicate)
    
def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
