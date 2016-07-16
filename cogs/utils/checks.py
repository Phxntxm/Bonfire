from discord.ext import commands
from . import config


def isOwner(ctx):
    return ctx.message.author.id == config.ownerID


def customPermsOrRole(perm):
    def predicate(ctx):
        nonlocal perm
        if ctx.message.channel.is_private:
            return False
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_perms))
        cmd = str(ctx.command)
        sid = ctx.message.server.id

        cursor.execute("show tables like %s", (sid,))
        result = cursor.fetchone()
        if result is not None:
            sql = "select perms from `" + sid + "` where command=%s"
            cursor.execute(sql, (cmd,))
            result = cursor.fetchone()
            if result is not None:
                perm = result['perms']
        if perm == "none":
            return True
        config.closeConnection()
        for role in ctx.message.author.roles:
            if getattr(role.permissions, perm):
                return True
        return False

    return commands.check(predicate)


def isPM():
    def predicate(ctx):
        return ctx.message.channel.is_private

    return commands.check(predicate)
