from discord.ext import commands
import discord
from .utils import checks
from .utils.config import getPhrase
import re


class Roles:
    """Class to handle management of roles on the server"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(aliases=['roles'], invoke_without_command=True, no_pm=True, pass_context=True)
    @checks.customPermsOrRole(manage_server=True)
    async def role(self, ctx):
        """This command can be used to modify the roles on the server.
        Pass no subcommands and this will print the roles currently available on this server"""
        server_roles = [role.name for role in ctx.message.server.roles if not role.is_everyone]
        await self.bot.say(getPhrase("ROLES:LIST_ROLES")+" ```\n{}```".format("\n".join(server_roles)))

    @role.command(name='remove', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(manage_server=True)
    async def remove_role(self, ctx):
        """Use this to remove roles from a number of members"""
        server_roles = [role for role in ctx.message.server.roles if not role.is_everyone]
        members = ctx.message.mentions
        if len(members) == 0:
            await self.bot.say(getPhrase("ROLES:ROLE_REMOVE_INIT"))
            msg = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel)
            if msg is None:
                await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
                return
            if len(msg.mentions) == 0:
                await self.bot.say(getPhrase("ROLES:ERROR_ROLE_NO_USER"))
                return
            members = msg.mentions

        await self.bot.say(getPhrase("ROLES:ROLE_REMOVE_LIST")+ " ```\n{}```".format("\n".join([r.name for r in server_roles])))
        msg = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_REMOVE_TIMEOUT"))
            return
        role_names = re.split(', ?', msg.content)
        roles = []
        for role in role_names:
            _role = discord.utils.get(server_roles, name=role)
            if _role is not None:
                roles.append(_role)

        if len(roles) == 0:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_INVALID_ROLE"))
            return

        for member in members:
            await self.bot.remove_roles(member, *roles)
        await self.bot.say(getPhrase("ROLES:ROLE_REMOVE_COMPLETE").format("\n".join(role_names), "\n".join([m.display_name for m in members])))

    @role.command(name='add', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(manage_server=True)
    async def add_role(self, ctx):
        """Use this to add a role to multiple members.
        Provide the list of members, and I'll ask for the role
        If no members are provided, I'll first ask for them"""
        server_roles = [role for role in ctx.message.server.roles if not role.is_everyone]
        members = ctx.message.mentions
        if len(members) == 0:
            await self.bot.say(getPhrase("ROLES:ROLE_ADD_INIT"))
            msg = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel)
            if msg is None:
                await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
                return
            if len(msg.mentions) == 0:
                await self.bot.say(getPhrase("ROLES:ERROR_ROLE_NO_USER"))
                return
            members = msg.mentions

        await self.bot.say(getPhrase("ROLES:ROLE_ADD_LIST")+" ```\n{}```".format("\n".join([r.name for r in server_roles])))

        msg = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
            return
        role_names = re.split(', ?', msg.content)
        roles = []
        for role in role_names:
            _role = discord.utils.get(server_roles, name=role)
            if _role is not None:
                roles.append(_role)

        if len(roles) == 0:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_INVALID_ROLE"))
            return

        for member in members:
            await self.bot.add_roles(member, *roles)
        await self.bot.say(getPhrase("ROLES:ROLE_ADD_COMPLETE").format("\n".join(role_names), "\n".join([m.display_name for m in members])))

    @role.command(name='delete', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(manage_server=True)
    async def delete_role(self, ctx, *, role: discord.Role = None):
        """This command can be used to delete one of the roles from the server"""
        if role is None:
            server_roles = [role for role in ctx.message.server.roles if not role.is_everyone]

            await self.bot.say(getPhrase("ROLES:ROLE_SERVERREMOVE_INIT")+" ```\n{}```".format("\n".join([r.name for r in server_roles])))
            check = lambda m: discord.utils.get(server_roles, name=m.content)
            msg = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel, check=check)
            if msg is None:
                await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
                return
            role = discord.utils.get(server_roles, name=msg.content)

        await self.bot.delete_role(ctx.message.server, role)
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERREMOVE_COMPLETE").format(role.name))

    @role.command(name='create', pass_context=True, no_pm=True)
    @checks.customPermsOrRole(manage_server=True)
    async def create_role(self, ctx):
        """This command can be used to create a new role for this server
        A prompt will follow asking what settings you would like for this new role
        I'll then ask if you'd like to set anyone to use this role"""
        # No use in running through everything if the bot cannot create the role
        if not ctx.message.server.me.permissions_in(ctx.message.channel).manage_roles:
            await self.bot.say(getPhrase("ROLES:ERROR_SERVERROLE_CREATE_NOPERMS"))
            return

        # Save a couple variables that will be used repeatedly
        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel

        # A couple checks that will be used in the wait_for_message's
        num_separated_check = lambda m: re.search("\d(,| )", m.content) is not None
        yes_no_check = lambda m: re.search("(yes|no)", m.content.lower()) is not None
        members_check = lambda m: len(m.mentions) > 0

        # Start the checks for the role, get the name of the command first
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERROLE_CREATE_INIT"))
        msg = await self.bot.wait_for_message(timeout=60.0, author=author, channel=channel)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
            return
        name = msg.content

        # Print a list of all the permissions available, then ask for which ones need to be active on this new role
        all_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]
        fmt = "\n".join("{}) {}".format(i, perm) for i, perm in enumerate(all_perms))
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERROLE_CREATE_PERMS")+"\n```\n{}```".format(fmt))
        msg = await self.bot.wait_for_message(timeout=60.0, author=author, channel=channel, check=num_separated_check)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
            return

        # Check if any integer's were provided that are within the length of the list of permissions
        num_permissions = [int(i) for i in re.split(' ?,?', msg.content) if i.isdigit() and int(i) < len(all_perms)]
        if len(num_permissions) == 0:
            await self.bot.say(getPhrase("ROLES:ERROR_INVALID_NUMBERS"))
            return

        # Check if this role should be in a separate section on the sidebard, i.e. hoisted
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERROLE_CREATE_SIDEBAR"))
        msg = await self.bot.wait_for_message(timeout=60.0, author=author, channel=channel, check=yes_no_check)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
            return
        hoist = True if "yes" in msg.content.lower() else False

        # Check if this role should be able to be mentioned
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERROLE_CREATE_MENTIONS"))
        msg = await self.bot.wait_for_message(timeout=60.0, author=author, channel=channel, check=yes_no_check)
        if msg is None:
            await self.bot.say(getPhrase("ROLES:ERROR_ROLE_TIMEOUT"))
            return
        mentionable = True if "yes" in msg.content.lower() else False

        # Ready to actually create the role
        perms = discord.Permissions.none()
        for index in num_permissions:
            setattr(perms, all_perms[index], True)

        payload = {
            'name': name,
            'permissions': perms,
            'hoist': hoist,
            'mentionable': mentionable
        }
        role = await self.bot.create_role(server, **payload)
        await self.bot.say(getPhrase("ROLES:ROLE_SERVERROLE_CREATE_COMPLETE").format(role.name))
        msg = await self.bot.wait_for_message(timeout=60.0, author=author, channel=channel, check=members_check)
        if msg is None:
            return
        for member in msg.mentions:
            await self.bot.add_roles(member, role)

        fmt = "\n".join(m.display_name for m in msg.mentions)
        await self.bot.say((getPhrase("ROLES:ROLE_ADD_COMPLETE")+" ```\n{1}```").format(name, fmt))


def setup(bot):
    bot.add_cog(Roles(bot))
