from discord.ext import commands
from .utils import checks
from .utils import config
import pymysql
import discord
import re

valid_perms = ['kick_members', 'ban_members', 'administrator', 'manage_channels', 'manage_server', 'read_messages',
               'send_messages', 'send_tts_messages', 'manage_messages', 'embed_links', 'attach_files',
               'read_message_history',
               'mention_everyone', 'connect', 'speak', 'mute_members', 'deafen_members', 'move_members',
               'use_voice_activation',
               'change_nicknames', 'manage_nicknames', 'manage_roles']


class Mod:
    """Commands that can be used by a or an admin, depending on the command"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True)
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed: {0.subcommand_passed}'.format(ctx))

    @nsfw.command(name="add", pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def nsfw_add(self, ctx):
        """Registers this channel as a 'nsfw' channel"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        try:
            cursor.execute('insert into nsfw_channels (channel_id) values ("{}")'.format(ctx.message.channel.id))
        except pymysql.IntegrityError:
            await self.bot.say("This channel is already registered as 'nsfw'!")
            config.closeConnection()
            return
        config.closeConnection()
        await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")

    @nsfw.command(name="remove", aliases=["delete"], pass_context=True)
    @checks.customPermsOrRole("kick_members")
    async def nsfw_remove(self, ctx, no_pm=True):
        """Removes this channel as a 'nsfw' channel"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from nsfw_channels where channel_id="{}"'.format(ctx.message.channel.id))
        if cursor.fetchone() is None:
            await self.bot.say("This channel is not registered as a ''nsfw' channel!")
            config.closeConnection()
            return

        cursor.execute('delete from nsfw_channels where channel_id="{}"'.format(ctx.message.channel.id))
        config.closeConnection()
        await self.bot.say("This channel has just been unregistered as a nsfw channel")

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("manage_server")
    async def leave(self, ctx):
        """Forces the bot to leave the server"""
        await self.bot.say('Why must I leave? Hopefully I can come back :c')
        await self.bot.leave_server(ctx.message.server)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def say(self, ctx, *msg: str):
        """Tells the bot to repeat what you say"""
        msg = ' '.join(msg)
        await self.bot.say(msg)
        await self.bot.delete_message(ctx.message)

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    async def perms(self, ctx, *command: str):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions"""
        if command is None:
            await self.bot.say("Valid permissions are: ```{}```".format("\n".join("{}".format(i) for i in valid_perms)))
            return
        command = " ".join(command)

        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_perms))
        cursor.execute("show tables like '{}'".format(ctx.message.server.id))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("There are no custom permissions setup on this server yet!")
            return
        sql = "select perms from `" + ctx.message.server.id + "` where command=%s"
        cursor.execute(sql, (command,))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("That command has no custom permissions setup on it!")
            return

        await self.bot.say(
            "You need to have the permission `{}` to use the command `{}` in this server".format(result['perms'],
                                                                                                 command))

    @perms.command(name="add", aliases=["setup,create"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def add_perms(self, ctx, *msg: str):
        """Sets up custom permissions on the provided command
        Format must be 'perms add <command> <permission>'
        If you want to open the command to everyone, provide 'none' as the permission"""
        command = " ".join(msg[0:len(msg)-1])
        permissions = msg[len(msg)-1]
        msg = msg[0:len(msg)-1]
        count = 0
        cmd = self.bot.commands.get(msg[count])
        while isinstance(cmd, commands.Group):
            count += 1
            try:
                cmd = cmd.commands.get(msg[count])
            except:
                break
    
        """Need to also check here if this is perms add or perms remove, 
        do not want to allow anyone less than an admin to access these no matter what"""
        for check in cmd.checks:
            if "isOwner" == check.__name__ or "has_permissions" == re.search("has_permissions",str(check)).group(0):
                await self.bot.say("This command cannot have custom permissions setup!")
                return

        if getattr(discord.Permissions, permissions, None) is None and not permissions.lower() == "none":
            await self.bot.say("{} does not appear to be a valid permission! Valid permissions are: ```{}```"
                               .format(permissions, "\n".join(valid_perms)))
        else:
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_perms))
            cursor.execute("show tables like %s", (ctx.message.server.id,))
            result = cursor.fetchone()
            if result is None:
                # Server's data doesn't exist yet, need to create it
                sql = "create table `" + ctx.message.server.id + "` (`command` varchar(32) not null,`perms` " \
                                                                 "varchar(32) not null,primary key (`command`))" \
                                                                 " engine=InnoDB default charset=utf8 collate=utf8_bin"
                cursor.execute(sql)
                sql = "insert into `" + ctx.message.server.id + "` (command, perms) values(%s, %s)"
                cursor.execute(sql, (command, permissions))
            else:
                sql = "select perms from `" + ctx.message.server.id + "`where command=%s"
                cursor.execute(sql, (command,))
                if cursor.fetchone() is None:
                    sql = "insert into `" + ctx.message.server.id + "` (command, perms) values(%s, %s)"
                    cursor.execute(sql, (command, permissions))
                else:
                    sql = "update `" + ctx.message.server.id + "` set perms=%s where command=%s"
                    cursor.execute(sql, (permissions, command))

        await self.bot.say("I have just added your custom permissions; "
                           "you now need to have `{}` permissions to use the command `{}`".format(permissions, command))
        config.closeConnection()
        
    @perms.command(name="remove", aliases=["delete"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def remove_perms(self, ctx, *command: str):
        """Removes the custom permissions setup on the command specified"""
        cmd = " ".join(command)
        sid = ctx.message.server.id
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_perms))
        cursor.execute("show tables like %s", (sid,))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("You do not have custom permissions setup on this server yet!")
            return
        sql = "select * from `"+sid+"` where command=%s"
        cursor.execute(sql, (cmd,))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("You do not have custom permissions setup on this command yet!")
            return
        sql = "delete from `"+sid+"` where command=%s"
        cursor.execute(sql, (cmd,))
        await self.bot.say("I have just removed the custom permissions for {}!".format(cmd))
        config.closeConnection()

def setup(bot):
    bot.add_cog(Mod(bot))
