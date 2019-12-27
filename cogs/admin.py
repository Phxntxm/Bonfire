import discord
import utils

from asyncpg import UniqueViolationError
from discord.ext import commands

valid_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]


class Admin(commands.Cog):
    """These are commands that allow more intuitive configuration, that don't fit into the config command"""

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def disable(self, ctx, *, command):
        """Disables the use of a command on this server"""
        if command == "disable" or command == "enable":
            await ctx.send("You cannot disable `{}`".format(command))
            return

        cmd = ctx.bot.get_command(command)
        if cmd is None:
            await ctx.send("No command called `{}`".format(command))
            return

        try:
            await ctx.bot.db.execute(
                "INSERT INTO restrictions (source, destination, from_to, guild) VALUES ($1, 'everyone', 'from', $2)",
                cmd.qualified_name,
                ctx.guild.id
            )
        except UniqueViolationError:
            await ctx.send(f"{cmd.qualified_name} is already disabled")
        else:
            await ctx.send(f"{cmd.qualified_name} is now disabled")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def enable(self, ctx, *, command):
        """Enables the use of a command on this server"""
        cmd = ctx.bot.get_command(command)
        if cmd is None:
            await ctx.send("No command called `{}`".format(command))
            return

        query = f"""
DELETE FROM restrictions WHERE
source=$1 AND
from_to='from' AND
destination='everyone' AND
guild=$2
"""
        await ctx.bot.db.execute(query, cmd.qualified_name, ctx.guild.id)
        await ctx.send(f"{cmd.qualified_name} is no longer disabled")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def notify(self, ctx, role: discord.Role, *, message):
        """
        Notify everyone in "role" with "message"
        This sets the role to mentionable, mentions the role, then sets it back
        """
        if not ctx.me.guild_permissions.manage_roles:
            await ctx.send("I do not have permissions to edit roles (this is required to complete this command)")
            return
        try:
            await role.edit(mentionable=True)
        except discord.Forbidden:
            await ctx.send("I do not have permissions to edit that role. "
                           "(I either don't have manage roles permissions, or it is higher on the hierarchy)")
        else:
            fmt = f"{role.mention}\n{message}"
            await ctx.send(fmt)
            await role.edit(mentionable=False)
            await ctx.message.delete()

    @commands.command()
    @commands.guild_only()
    @utils.can_run(kick_members=True)
    async def restrictions(self, ctx):
        """Used to list all the current restrictions set

        EXAMPLE: !restrictions
        RESULT: All the current restrictions"""
        restrictions = await ctx.bot.db.fetch(
            "SELECT source, destination, from_to FROM restrictions WHERE guild=$1",
            ctx.guild.id
        )

        entries = []
        for restriction in restrictions:
            # Check whether it's from or to to change what the format looks like
            dest = restriction["destination"]
            if dest != "everyone":
                dest = await utils.convert(ctx, restriction["destination"])
            # If it doesn't exist, don't add it
            if dest:
                entries.append(f"{restriction['source']} {'from' if restriction['from_to'] == 'from' else 'to'} {dest}")

        if entries:
            # Then paginate
            try:
                pages = utils.Pages(ctx, entries=entries)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))
        else:
            await ctx.send("There are no restrictions!")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def restrict(self, ctx, *options):
        """
        This is an intuitive command to restrict something to/from something
        The format is `!restrict what from/to who/where`

        For example, `!restrict command to role` will require a user to have `role`
        to be able to run `command`
        `!restrict command to channel` will only allow `command` to be ran in `channel`

        EXAMPLE: !restrict boop from @user
        RESULT: This user can no longer use the boop command
        """
        # First make sure we're given three options
        if len(options) != 3:
            await ctx.send("You need to provide 3 options! Such as `command from @User`")
            return
        elif ctx.message.mention_everyone:
            await ctx.send("Please do not use this command to 'disable from everyone'. Use the `disable` command")
            return
        else:
            # Get the three arguments from this list, then make sure the 2nd is either from or to
            arg1, arg2, arg3 = options
            if arg2.lower() not in ['from', 'to']:
                await ctx.send("The 2nd option needs to be either \"to\" or \"from\". Such as: `command from @user` "
                               "or `command to Role`")
                return
            else:
                # Try to convert the other arguments
                arg2 = arg2.lower()
                option1 = await utils.convert(ctx, arg1)
                option2 = await utils.convert(ctx, arg3)
                if option1 is None or option2 is None:
                    await ctx.send("Sorry, but I don't know how to restrict {} {} {}".format(arg1, arg2, arg3))
                    return

        from_to = arg2
        source = None
        destination = None
        overwrites = None

        # The possible options:
        # Member
        # Role
        # Command
        # Text/Voice Channel

        if isinstance(option1, (commands.core.Command, commands.core.Group)):
            # From:
            # Users - Command can't be run by this person
            # Channels - Command can't be ran in this channel
            # Roles - Command can't be ran by anyone in this role (least likely, but still possible uses)
            if arg2 == "from":
                if isinstance(option2, (discord.Member, discord.Role, discord.TextChannel)):
                    source = option1.qualified_name
                    destination = str(option2.id)
            # To:
            # Channels - Command can only be run in this channel
            # Roles - This role is required in order to run this command
            else:
                if isinstance(option2, (discord.Role, discord.TextChannel)):
                    source = option1.qualified_name
                    destination = str(option2.id)
        elif isinstance(option1, discord.Member):
            # From:
            # Channels - Setup an overwrite for this channel so that they cannot read it
            # Command - Command cannot be used by this user
            if arg2 == "from":
                if isinstance(option2, (discord.TextChannel, discord.VoiceChannel)):
                    ov = discord.utils.find(lambda t: t[0] == option1, option2.overwrites)
                    if ov:
                        ov = ov[1]
                        ov.update(read_messages=False)
                    else:
                        ov = discord.PermissionOverwrite(read_messages=False)
                    overwrites = {
                        'channel': option2,
                        option1: ov
                    }
                elif isinstance(option2, (commands.core.Command, commands.core.Group)):
                    source = option2.qualified_name
                    destination = str(option1.id)
        elif isinstance(option1, (discord.TextChannel, discord.VoiceChannel)):
            # From:
            # Command - Command cannot be used in this channel
            # Member - Setup an overwrite for this channel so that they cannot read it
            # Role - Setup an overwrite for this channel so that this Role cannot read it
            if arg2 == "from":
                if isinstance(option2, (discord.Member, discord.Role)):
                    ov = discord.utils.find(lambda t: t[0] == option2, option1.overwrites)
                    if ov:
                        ov = ov[1]
                        ov.update(read_messages=False)
                    else:
                        ov = discord.PermissionOverwrite(read_messages=False)
                    overwrites = {
                        'channel': option1,
                        option2: ov
                    }
                elif isinstance(option2, (commands.core.Command, commands.core.Group)) \
                        and isinstance(option1, discord.TextChannel):
                    source = option2.qualified_name
                    destination = str(option1.id)
            # To:
            # Command - Command can only be used in this channel
            # Role - Setup an overwrite so only this role can read this channel
            else:
                if isinstance(option2, (commands.core.Command, commands.core.Group)) \
                        and isinstance(option1, discord.TextChannel):
                    source = option2.qualified_name
                    destination = str(option1.id)
                elif isinstance(option2, (discord.Member, discord.Role)):
                    ov = discord.utils.find(lambda t: t[0] == option2, option1.overwrites)
                    if ov:
                        ov = ov[1]
                        ov.update(read_messages=True)
                    else:
                        ov = discord.PermissionOverwrite(read_messages=True)
                    ov2 = discord.utils.find(lambda t: t[0] == ctx.message.guild.default_role,
                                             option1.overwrites)
                    if ov2:
                        ov2 = ov2[1]
                        ov2.update(read_messages=False)
                    else:
                        ov2 = discord.PermissionOverwrite(read_messages=False)
                    overwrites = {
                        'channel': option1,
                        option2: ov,
                        ctx.message.guild.default_role: ov2
                    }
        elif isinstance(option1, discord.Role):
            # From:
            # Command - No one with this role can run this command
            # Channel - Setup an overwrite for this channel so that this Role cannot read it
            if arg2 == "from":
                if isinstance(option2, (commands.core.Command, commands.core.Group)):
                    source = option2.qualified_name
                    destination = option1.id
                elif isinstance(option2, (discord.TextChannel, discord.VoiceChannel)):
                    ov = discord.utils.find(lambda t: t[0] == option1, option2.overwrites)
                    if ov:
                        ov = ov[1]
                        ov.update(read_messages=False)
                    else:
                        ov = discord.PermissionOverwrite(read_messages=False)
                    overwrites = {
                        'channel': option2,
                        option1: ov
                    }
            # To:
            # Command - You have to have this role to run this command
            # Channel - Setup an overwrite so you have to have this role to read this channel
            else:
                if isinstance(option2, (discord.TextChannel, discord.VoiceChannel)):
                    ov = discord.utils.find(lambda t: t[0] == option1, option2.overwrites)
                    if ov:
                        ov = ov[1]
                        ov.update(read_messages=True)
                    else:
                        ov = discord.PermissionOverwrite(read_messages=True)
                    ov2 = discord.utils.find(lambda t: t[0] == ctx.message.guild.default_role,
                                             option2.overwrites)
                    if ov2:
                        ov2 = ov2[1]
                        ov2.update(read_messages=False)
                    else:
                        ov2 = discord.PermissionOverwrite(read_messages=False)
                    overwrites = {
                        'channel': option2,
                        option1: ov,
                        ctx.message.guild.default_role: ov2
                    }
                elif isinstance(option2, (commands.core.Command, commands.core.Group)):
                    source = option2.qualified_name
                    destination = str(option1.id)

        if source is not None and destination is not None:
            try:
                await ctx.bot.db.execute(
                    "INSERT INTO restrictions (guild, source, destination, from_to) VALUES ($1, $2, $3, $4)",
                    ctx.guild.id,
                    source,
                    destination,
                    from_to
                )
            except UniqueViolationError:
                # If it's already inserted, then nothing needs to be updated
                # It just means this particular restriction is already set
                pass
            else:
                ctx.bot.cache.add_restriction(ctx.guild, from_to, {"source": source, "destination": destination})
        elif overwrites:
            channel = overwrites.pop('channel')
            for target, setting in overwrites.items():
                await channel.set_permissions(target, overwrite=setting)
        else:
            await ctx.send("Sorry but I don't know how to restrict {} {} {}".format(arg1, arg2, arg3))
            return

        await ctx.send("I have just restricted {} {} {}".format(arg1, arg2, arg3))

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
    async def unrestrict(self, ctx, *options):
        """
        This is an intuitive command to unrestrict something to/from something
        The format is `!restrict what from/to who/where`

        For example, `!unrestrict command to role` will remove the restriction on this command, requiring role

        EXAMPLE: !unrestrict boop from @user
        RESULT: The restriction on this user to use boop has been lifted
        """
        # First make sure we're given three options
        if len(options) != 3:
            await ctx.send("You need to provide 3 options! Such as `command from @User`")
            return
        else:
            # Get the three arguments from this list, then make sure the 2nd is either from or to
            arg1, arg2, arg3 = options
            if arg2.lower() not in ['from', 'to']:
                await ctx.send("The 2nd option needs to be either \"to\" or \"from\". Such as: `command from @user` "
                               "or `command to Role`")
                return
            else:
                # Try to convert the other arguments
                arg2 = arg2.lower()
                option1 = await utils.convert(ctx, arg1)
                option2 = await utils.convert(ctx, arg3)
                if option1 is None or option2 is None:
                    await ctx.send("Sorry, but I don't know how to unrestrict {} {} {}".format(arg1, arg2, arg3))
                    return

        # First check if this is a blacklist/whitelist (by checking if we are unrestricting commands)
        if any(isinstance(x, (commands.core.Command, commands.core.Group)) for x in [option1, option2]):
            # The source should always be the command, so just set this based on which order is given (either is
            # allowed)
            if isinstance(option1, (commands.core.Command, commands.core.Group)):
                source = option1.qualified_name
                destination = str(option2.id)
            else:
                source = option2.qualified_name
                destination = str(option1.id)

            # Now just try to remove it
            await ctx.bot.db.execute("""
DELETE FROM
    restrictions
WHERE
    source=$1 AND 
    destination=$2 AND 
    from_to=$3 AND 
    guild=$4""", source, destination, arg2, ctx.guild.id)
            ctx.bot.cache.remove_restriction(ctx.guild.id, arg2, {"source": source, "destination": destination})

        # If this isn't a blacklist/whitelist, then we are attempting to remove an overwrite
        else:
            # Get the source and destination based on whatever order is provided
            if isinstance(option1, (discord.TextChannel, discord.VoiceChannel)):
                source = option2
                destination = option1
            else:
                source = option1
                destination = option2

            # See if it's the blacklist that we're removing from
            if arg2 == "from":
                # Get overwrites if they exist
                # If it doesn't, there's nothing to do here
                ov = discord.utils.find(lambda t: t[0] == source, destination.overwrites)
                if ov:
                    ov = ov[1]
                    ov.update(read_messages=True)
                    await destination.set_permissions(source, overwrite=ov)
            else:
                ov = discord.utils.find(lambda t: t[0] == source, destination.overwrites)
                ov2 = discord.utils.find(lambda t: t[0] == ctx.message.guild.default_role, destination.overwrites)
                if ov:
                    ov = ov[1]
                    ov.update(read_messages=None)
                    await destination.set_permissions(source, overwrite=ov)
                if ov2:
                    ov2 = ov2[1]
                    ov2.update(read_messages=True)
                    await destination.set_permissions(source, overwrite=ov2)

        await ctx.send("I have just unrestricted {} {} {}".format(arg1, arg2, arg3))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def perms(self, ctx, *, command: str):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions

        EXAMPLE: !perms help
        RESULT: Hopefully a result saying you just need send_messages permissions; otherwise lol
        this server's admin doesn't like me """
        cmd = ctx.bot.get_command(command)

        if cmd is None:
            # If a command wasn't provided, see if a user was
            converter = commands.converter.MemberConverter()
            try:
                member = await converter.convert(ctx, command)
            # If we failed to convert, just mention that an invalid command was provided
            except commands.converter.BadArgument:
                await ctx.send("That is not a valid command!")
                return
            else:
                # Otherwise iterate through the permissions and their values, only including ones that are on
                perms = [p for p, value in member.guild_permissions if value]
                # Create an embed with their colour
                embed = discord.Embed(colour=member.colour)
                # Set the author to this user
                embed.set_author(name=str(member), icon_url=member.avatar_url)
                # Then add their permissions in one field
                embed.add_field(name="Allowed permissions", value="\n".join(perms))
                await ctx.send(embed=embed)
                return
        result = await ctx.bot.db.fetchrow(
            "SELECT permission FROM custom_permissions WHERE guild = $1 AND command = $2",
            ctx.guild.id,
            command
        )
        perms_value = result["permission"] if result else None

        if perms_value is None:
            # If we don't find custom permissions, get the required permission for a command
            # based on what we set in utils.can_run, if can_run isn't found, we'll get an IndexError
            try:
                can_run = [func for func in cmd.checks if "can_run" in func.__qualname__][0]
            except IndexError:
                # Loop through and check if there is a check called is_owner
                # If we loop through and don't find one, this means that the only other choice is to be
                # Able to manage the server (for the utils on perm commands)
                for func in cmd.checks:
                    if "is_owner" in func.__qualname__:
                        await ctx.send("You need to own the bot to run this command")
                        return
                await ctx.send("You are required to have `manage_guild` permissions to run `{}`".format(
                    cmd.qualified_name
                ))
                return

            # Perms will be an attribute if can_run is found no matter what, so no need to check this
            perms = "\n".join(attribute for attribute, setting in can_run.perms.items() if setting)
            await ctx.send(
                "You are required to have `{}` permissions to run `{}`".format(perms, cmd.qualified_name))
        else:
            # Permissions are saved as bit values, so create an object based on that value
            # Then check which permission is true, that is our required permission
            # There's no need to check for errors here, as we ensure a permission is valid when adding it
            permissions = discord.Permissions(perms_value)
            needed_perm = [perm[0] for perm in permissions if perm[1]][0]
            await ctx.send("You need to have the permission `{}` "
                           "to use the command `{}` in this server".format(needed_perm, command))

    @perms.command(name="add", aliases=["setup,create"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_perms(self, ctx, *, msg: str):
        """Sets up custom permissions on the provided command
        Format must be 'perms add <command> <permission>'
        If you want to open the command to everyone, provide 'none' as the permission

        EXAMPLE: !perms add skip ban_members
        RESULT: No more random people voting to skip a song"""

        # Since subcommands exist, base the last word in the list as the permission, and the rest of it as the command
        command, _, permission = msg.rpartition(" ")
        if command == "":
            await ctx.send("Please provide the permissions you want to setup, the format for this must be in:\n"
                           "`perms add <command> <permission>`")
            return

        cmd = ctx.bot.get_command(command)

        if cmd is None:
            await ctx.send(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        # If a user can run a command, they have to have send_messages permissions; so use this as the base
        if permission.lower() == "none":
            permission = "send_messages"

        # Convert the string to an int value of the permissions object, based on the required permission
        # If we hit an attribute error, that means the permission given was not correct
        perm_obj = discord.Permissions.none()
        try:
            setattr(perm_obj, permission, True)
        except AttributeError:
            await ctx.send("{} does not appear to be a valid permission! Valid permissions are: ```\n{}```"
                           .format(permission, "\n".join(valid_perms)))
            return
        perm_value = perm_obj.value

        # Two cases I use should never have custom permissions setup on them, is_owner for obvious reasons
        # The other case is if I'm using the default has_permissions case
        # Which means I do not want to check custom permissions at all
        # Currently the second case is only on adding and removing permissions, to avoid abuse on these
        for check in cmd.checks:
            if "is_owner" == check.__name__ or "has_permissions" in str(check):
                await ctx.send("This command cannot have custom permissions setup!")
                return

        await ctx.bot.db.execute(
            "INSERT INTO custom_permissions (guild, command, permission) VALUES ($1, $2, $3)",
            ctx.guild.id,
            cmd.qualified_name,
            perm_value
        )

        ctx.bot.cache.update_custom_permission(ctx.guild, cmd.qualified_name, perm_value)

        await ctx.send("I have just added your custom permissions; "
                       "you now need to have `{}` permissions to use the command `{}`".format(permission, command))

    @perms.command(name="remove", aliases=["delete"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def remove_perms(self, ctx, *, command: str):
        """Removes the custom permissions setup on the command specified

        EXAMPLE: !perms remove play
        RESULT: Freedom!"""

        cmd = ctx.bot.get_command(command)

        if cmd is None:
            await ctx.send(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        await ctx.bot.db.execute(
            "DELETE FROM custom_permissions WHERE guild=$1 AND command=$2", ctx.guild.id, cmd.qualified_name
        )

        ctx.bot.cache.update_custom_permission(ctx.guild, cmd.qualified_name, None)

        await ctx.send("I have just removed the custom permissions for {}!".format(cmd))

    @commands.command(aliases=['nick'])
    @commands.guild_only()
    @utils.can_run(kick_members=True)
    async def nickname(self, ctx, *, name=None):
        """Used to set the nickname for Bonfire (provide no nickname and it will reset)

        EXAMPLE: !nick Music Bot
        RESULT: My nickname is now Music Bot"""
        try:
            await ctx.message.guild.me.edit(nick=name)
        except discord.HTTPException:
            await ctx.send("Sorry but I can't change my nickname to {}".format(name))
        else:
            await ctx.send("\N{OK HAND SIGN}")


def setup(bot):
    bot.add_cog(Admin())
