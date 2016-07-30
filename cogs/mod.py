from discord.ext import commands
from .utils import checks
from .utils import config
import discord
import re

valid_perms = list(dict(discord.Permissions.none()))


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
        nsfw_channels = config.getContent('nsfw_channels')
        if ctx.message.channel.id in nsfw_channels:
            await self.bot.say("This channel is already registered as 'nsfw'!")
        else:
            nsfw_channels.append(ctx.message.channel.id)
            config.saveContent('nsfw_channels', nsfw_channels)
            await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")

    @nsfw.command(name="remove", aliases=["delete"], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel"""
        nsfw_channels = config.getContent('nsfw_channels')
        if ctx.message.channel.id not in nsfw_channels:
            await self.bot.say("This channel is not registered as a ''nsfw' channel!")
        else:
            nsfw_channels.remove(ctx.message.channel.id)
            config.saveContent('nsfw_channels', nsfw_channels)
            await self.bot.say("This channel has just been unregistered as a nsfw channel")

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("manage_server")
    async def leave(self, ctx):
        """Forces the bot to leave the server"""
        await self.bot.say('Why must I leave? Hopefully I can come back :c')
        await self.bot.leave_server(ctx.message.server)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say"""
        await self.bot.say(msg)
        await self.bot.delete_message(ctx.message)

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def perms(self, ctx, *, command: str):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions"""
        if command is None or len(command) == 0:
            await self.bot.say("Valid permissions are: ```{}```".format("\n".join("{}".format(i) for i in valid_perms)))
            return
        command = " ".join(command)

        custom_perms = config.getContent('custom_permissions') or {}
        server_perms = custom_perms.get(ctx.message.server.id)
        if server_perms is None:
            await self.bot.say("There are no custom permissions setup on this server yet!")
            return
            
        command_perms = server_perms.get(command)
        if command_perms is None:
            await self.bot.say("That command has no custom permissions setup on it!")
        else:
            await self.bot.say("You need to have the permission `{}` "
                               "to use the command `{}` in this server".format(command_perms, command))

    @perms.command(name="add", aliases=["setup,create"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def add_perms(self, ctx, *msg: str):
        """Sets up custom permissions on the provided command
        Format must be 'perms add <command> <permission>'
        If you want to open the command to everyone, provide 'none' as the permission"""
        command = " ".join(msg[0:len(msg) - 1])
        permissions = msg[len(msg) - 1]
        
        #If a user can run the command, they have to have send_messages permissions; so use this as the base
        if permissions.lower() == "none":
            permissions = "send_messages"
        
        #Convert the string to an int value of the permissions obj, based on the required permission
        perm_obj = discord.Permissions.none()
        setattr(perm_obj,permissions,True)
        perm_value = perm_obj.value
        
        cmd = None
        for part in permissions:
            try:
                if cmd is None:
                    cmd = self.bot.commands.get(part)
                else:
                    cmd = cmd.commands.get(part)
            except AttributeError:
                break
        
        if cmd is None:
            await self.bot.say("That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        for check in cmd.checks:
            if "isOwner" == check.__name__ or re.search("has_permissions", str(check)) is not None:
                await self.bot.say("This command cannot have custom permissions setup!")
                return

        if getattr(discord.Permissions, permissions, None) is None:
            await self.bot.say("{} does not appear to be a valid permission! Valid permissions are: ```{}```"
                               .format(permissions, "\n".join(valid_perms)))
            return

        custom_perms = config.getContent('custom_permissions') or {}
        server_perms = custom_perms.get(ctx.message.server.id) or {}
        server_perms[command] = perm_value
        custom_perms[ctx.message.server.id] = server_perms
        
        config.saveContent('custom_permissions', custom_perms)
        await self.bot.say("I have just added your custom permissions; "
                           "you now need to have `{}` permissions to use the command `{}`".format(permissions, command))

    @perms.command(name="remove", aliases=["delete"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def remove_perms(self, ctx, *command: str):
        """Removes the custom permissions setup on the command specified"""
        cmd = " ".join(command)
        custom_perms = config.getContent('custom_permissions') or {}
        server_perms = custom_perms.get(ctx.message.server.id)
        if server_perms is None:
            await self.bot.say("There are no custom permissions setup on this server yet!")
            return
        command_perms = server_perms.get(cmd)
        if command_perms is None:
            await self.bot.say("You do not have custom permissions setup on this command yet!")
            return
        del custom_perms[ctx.message.server.id][cmd]
        config.saveContent('custom_permissions', custom_perms)
        await self.bot.say("I have just removed the custom permissions for {}!".format(cmd))


def setup(bot):
    bot.add_cog(Mod(bot))
