from discord.ext import commands

from . import utils

import discord

import re

valid_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]


class Administration:
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
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

        from_entry = None
        to_entry = None
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
                    from_entry = {
                        'source': option1.qualified_name,
                        'destination': str(option2.id)
                    }
            # To:
            # Channels - Command can only be run in this channel
            # Roles - This role is required in order to run this command
            else:
                if isinstance(option2, (discord.Role, discord.TextChannel)):
                    to_entry = {
                        'source': option1.qualified_name,
                        'destination': str(option2.id)
                    }
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
                    from_entry = {
                        'source': option2.qualified_name,
                        'destination': str(option1.id)
                    }
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
                    from_entry = {
                        'source': option2.qualified_name,
                        'destination': str(option1.id)
                    }
            # To:
            # Command - Command can only be used in this channel
            # Role - Setup an overwrite so only this role can read this channel
            else:
                if isinstance(option2, (commands.core.Command, commands.core.Group)) \
                        and isinstance(option1, discord.TextChannel):
                    to_entry = {
                        'source': option2.qualified_name,
                        'destination': str(option1.id)
                    }
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
                    from_entry = {
                        'source': option2.qualified_name,
                        'destination': str(option1.id)
                    }
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
                    to_entry = {
                        'source': option2.qualified_name,
                        'destination': str(option1.id)
                    }

        if to_entry:
            restrictions = self.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='restrictions') or {}
            to = restrictions.get('to', [])
            if to_entry not in to:
                to.append(to_entry)
            update = {
                'server_id': str(ctx.message.guild.id),
                'restrictions': {
                    'to': to
                }
            }
            self.bot.db.save('server_settings', update)
        elif from_entry:
            restrictions = self.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='restrictions') or {}
            _from = restrictions.get('from', [])
            if from_entry not in _from:
                _from.append(from_entry)
            update = {
                'server_id': str(ctx.message.guild.id),
                'restrictions': {
                    'from': _from
                }
            }
            self.bot.db.save('server_settings', update)
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
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
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
                    await ctx.send("Sorry, but I don't know how to restrict {} {} {}".format(arg1, arg2, arg3))
                    return

        # First check if this is a blacklist/whitelist (by checking if we are unrestricting commands)
        if any(isinstance(x, (commands.core.Command, commands.core.Group)) for x in [option1, option2]):
            # The source should always be the command, so just set this based on which order is given (either is
            # allowed)
            if isinstance(option1, (commands.core.Command, commands.core.Group)):
                restriction = {
                    'source': option1.qualified_name,
                    'destination': str(option2.id)
                }
            else:
                restriction = {
                    'source': option2.qualified_name,
                    'destination': str(option1.id)
                }

            # Load restrictions
            restrictions = self.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='restrictions') or {}
            # Attempt to remove the restriction provided
            try:
                restrictions.get(arg2, []).remove(restriction)
            # If it doesn't exist, nothing is needed to be done
            except ValueError:
                await ctx.send("The restriction {} {} {} does not exist!".format(arg1, arg2, arg3))
                return
            # If it was removed succesfully, save the change and let the author know this has been done
            else:
                entry = {
                    'server_id': str(ctx.message.guild.id),
                    'restrictions': restrictions
                }
                self.bot.db.save('server_settings', entry)
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

    @commands.command(aliases=['nick'])
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    @utils.check_restricted()
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

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def ignore(self, ctx, member_or_channel):
        """This command can be used to have Bonfire ignore certain members/channels

        EXAMPLE: !ignore #general
        RESULT: Bonfire will ignore commands sent in the general channel"""
        key = ctx.message.guild.id

        converter = commands.converter.MemberConverter()
        member = None
        channel = None
        try:
            member = await converter.convert(ctx, member_or_channel)
        except commands.converter.BadArgument:
            converter = commands.converter.TextChannelConverter()
            try:
                channel = await converter.convert(ctx, member_or_channel)
            except commands.converter.BadArgument:
                await ctx.send("{} does not appear to be a member or channel!".format(member_or_channel))
                return

        settings = self.bot.db.load('server_settings', key=key, pluck='ignored') or {}
        ignored = settings.get('ignored', {'members': [], 'channels': []})
        if member:
            if str(member.id) in ignored['members']:
                await ctx.send("I am already ignoring {}!".format(member.display_name))
                return
            elif member.guild_permissions >= ctx.message.author.guild_permissions:
                await ctx.send("You cannot make me ignore someone at equal or higher rank than you!")
                return
            else:
                ignored['members'].append(str(member.id))
                fmt = "Ignoring {}".format(member.display_name)
        else:
            if str(channel.id) in ignored['channels']:
                await ctx.send("I am already ignoring {}!".format(channel.mention))
                return
            else:
                ignored['channels'].append(str(channel.id))
                fmt = "Ignoring {}".format(channel.mention)

        entry = {
            'ignored': ignored,
            'server_id': str(key)
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send(fmt)

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def unignore(self, ctx, member_or_channel):
        """This command can be used to have Bonfire stop ignoring certain members/channels

        EXAMPLE: !unignore #general
        RESULT: Bonfire will no longer ignore commands sent in the general channel"""
        key = str(ctx.message.guild.id)

        converter = commands.converter.MemberConverter()
        member = None
        channel = None
        try:
            member = await converter.convert(ctx, member_or_channel)
        except commands.converter.BadArgument:
            converter = commands.converter.TextChannelConverter()
            try:
                channel = await converter.convert(ctx, member_or_channel)
            except commands.converter.BadArgument:
                await ctx.send("{} does not appear to be a member or channel!".format(member_or_channel))
                return

        settings = self.bot.db.load('server_settings', key=key) or {}
        ignored = settings.get('ignored', {'members': [], 'channels': []})
        if member:
            if str(member.id) not in ignored['members']:
                await ctx.send("I'm not even ignoring {}!".format(member.display_name))
                return

            ignored['members'].remove(str(member.id))
            fmt = "I am no longer ignoring {}".format(member.display_name)
        else:
            if str(channel.id) not in ignored['channels']:
                await ctx.send("I'm not even ignoring {}!".format(channel.mention))
                return

            ignored['channels'].remove(str(channel.id))
            fmt = "I am no longer ignoring {}".format(channel.mention)

        entry = {
            'ignored': ignored,
            'server_id': str(key)
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send(fmt)

    @commands.command(aliases=['notifications'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def alerts(self, ctx, channel: discord.TextChannel):
        """This command is used to set a channel as the server's default 'notifications' channel
        Any notifications (like someone going live on Twitch, or Picarto) will go to that channel by default
        This can be overridden with specific alerts command, such as `!picarto alerts #channel`
        This command is just the default; the one used if there is no other one set.

        EXAMPLE: !alerts #alerts
        RESULT: No more alerts spammed in #general!"""
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications': {
                'default': str(channel.id)
            }
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send("I have just changed this server's default 'notifications' channel"
                       "\nAll notifications will now default to `{}`".format(channel))

    @commands.group(invoke_without_command=True, aliases=['goodbye'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def welcome(self, ctx, on_off: str):
        """This command can be used to set whether or not you want user notificaitons to show
        Provide on, yes, or true to set it on; otherwise it will be turned off

        EXAMPLE: !welcome on
        RESULT: Annoying join/leave notifications! Yay!"""
        # Join/Leave notifications can be kept separate from normal alerts
        # So we base this channel on it's own and not from alerts
        # When mod logging becomes available, that will be kept to it's own channel if wanted as well
        on_off = True if re.search("(on|yes|true)", on_off.lower()) else False

        entry = {
            'server_id': str(ctx.message.guild.id),
            'join_leave': on_off
        }

        self.bot.db.save('server_settings', entry)
        fmt = "notify" if on_off else "not notify"
        await ctx.send("This server will now {} if someone has joined or left".format(fmt))

    @welcome.command(name='alerts', aliases=['notifications'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def _welcome_alerts(self, ctx, *, channel: discord.TextChannel):
        """A command used to set the override for notifications about users joining/leaving

        EXAMPLE: !welcome alerts #notifications
        RESULT: All user joins/leaves will be sent to the #notificatoins channel"""
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications': {
                'welcome': str(channel.id)
            }
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send(
            "I have just changed this server's welcome/goodbye notifications channel to {}".format(channel.name))

    @welcome.command(name='message')
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def _welcome_message(self, ctx, *, msg = None):
        """A command to customize the welcome/goodbye message
        There are a couple things that can be set to customize the message
        {member} - Will mention the user joining
        {server} - Will display the server's name

        Give no message and it will be set to the default
        EXAMPLE: !welcome message {member} to {server}
        RESULT: Welcome Member#1234 to ServerName"""
        parent = ctx.message.content.split()[0]
        parent = parent[len(ctx.prefix):]

        if re.search("{.*token.*}", msg):
            await ctx.send("Illegal content in {} message".format(parent))
        else:
            entry = {
                'server_id': str(ctx.message.guild.id),
                parent + '_message': msg
            }
            self.bot.db.save('server_settings', entry)
            await ctx.send("I have just updated your {} message".format(parent))

    @commands.group()
    @utils.check_restricted()
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        # This command isn't meant to do anything, so just send an error if an invalid subcommand is passed
        pass

    @nsfw.command(name="add")
    @utils.custom_perms(kick_members=True)
    @utils.check_restricted()
    async def nsfw_add(self, ctx):
        """Registers this channel as a 'nsfw' channel

        EXAMPLE: !nsfw add
        RESULT: ;)"""

        if type(ctx.message.channel) is discord.DMChannel:
            key = 'DMs'
        else:
            key = str(ctx.message.guild.id)

        channels = self.bot.db.load('server_settings', key=key, pluck='nsfw_channels') or []
        channels.append(str(ctx.message.channel.id))

        entry = {
            'server_id': key,
            'nsfw_channels': channels
        }

        self.bot.db.save('server_settings', entry)

        await ctx.send("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")

    @nsfw.command(name="remove", aliases=["delete"])
    @utils.custom_perms(kick_members=True)
    @utils.check_restricted()
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel

        EXAMPLE: !nsfw remove
        RESULT: ;("""
        channel = str(ctx.message.channel.id)
        if type(ctx.message.channel) is discord.DMChannel:
            key = 'DMs'
        else:
            key = str(ctx.message.guild.id)

        channels = self.bot.db.load('server_settings', key=key, pluck='nsfw_channels') or []
        if channel in channels:
            channels.remove(channel)

            entry = {
                'server_id': key,
                'nsfw_channels': channels
            }
            self.bot.db.save('server_settings', entry)
            await ctx.send("This channel has just been unregistered as a nsfw channel")
        else:
            await ctx.send("This channel is not registerred as a nsfw channel!")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def perms(self, ctx, *, command: str = None):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions

        EXAMPLE: !perms help RESULT: Hopefully a result saying you just need send_messages permissions; otherwise lol
        this server's admin doesn't like me """
        if command is None:
            await ctx.send(
                "Valid permissions are: ```\n{}```".format("\n".join("{}".format(i) for i in valid_perms)))
            return

        cmd = self.bot.get_command(command)

        if cmd is None:
            await ctx.send("That is not a valid command!")
            return

        server_perms = self.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='permissions') or {}

        perms_value = server_perms.get(cmd.qualified_name)
        if perms_value is None:
            # If we don't find custom permissions, get the required permission for a command
            # based on what we set in utils.custom_perms, if custom_perms isn't found, we'll get an IndexError
            try:
                custom_perms = [func for func in cmd.checks if "custom_perms" in func.__qualname__][0]
            except IndexError:
                # Loop through and check if there is a check called is_owner
                # If we loop through and don't find one, this means that the only other choice is to be
                # Able to manage the server (for the utils on perm commands)
                for func in cmd.checks:
                    if "is_owner" in func.__qualname__:
                        await ctx.send("You need to own the bot to run this command")
                        return
                await ctx.send(
                    "You are required to have `manage_guild` permissions to run `{}`".format(cmd.qualified_name))
                return

            # Perms will be an attribute if custom_perms is found no matter what, so no need to check this
            perms = "\n".join(attribute for attribute, setting in custom_perms.perms.items() if setting)
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
    @utils.check_restricted()
    async def add_perms(self, ctx, *msg: str):
        """Sets up custom permissions on the provided command
        Format must be 'perms add <command> <permission>'
        If you want to open the command to everyone, provide 'none' as the permission

        EXAMPLE: !perms add skip ban_members
        RESULT: No more random people voting to skip a song"""

        # Since subcommands exist, base the last word in the list as the permission, and the rest of it as the command
        command = " ".join(msg[0:len(msg) - 1])
        if command == "":
            await ctx.send("Please provide the permissions you want to setup, the format for this must be in:\n"
                           "`perms add <command> <permission>`")
            return
        try:
            permissions = msg[len(msg) - 1]
        except IndexError:
            await ctx.send("Please provide the permissions you want to setup, the format for this must be in:\n"
                           "`perms add <command> <permission>`")
            return

        cmd = self.bot.get_command(command)

        if cmd is None:
            await ctx.send(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        # If a user can run a command, they have to have send_messages permissions; so use this as the base
        if permissions.lower() == "none":
            permissions = "send_messages"

        # Convert the string to an int value of the permissions object, based on the required permission
        # If we hit an attribute error, that means the permission given was not correct
        perm_obj = discord.Permissions.none()
        try:
            setattr(perm_obj, permissions, True)
        except AttributeError:
            await ctx.send("{} does not appear to be a valid permission! Valid permissions are: ```\n{}```"
                           .format(permissions, "\n".join(valid_perms)))
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

        entry = {
            'server_id': str(ctx.message.guild.id),
            'permissions': {cmd.qualified_name: perm_value}
        }

        self.bot.db.save('server_settings', entry)

        await ctx.send("I have just added your custom permissions; "
                       "you now need to have `{}` permissions to use the command `{}`".format(permissions, command))

    @perms.command(name="remove", aliases=["delete"])
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @utils.check_restricted()
    async def remove_perms(self, ctx, *, command: str):
        """Removes the custom permissions setup on the command specified

        EXAMPLE: !perms remove play
        RESULT: Freedom!"""

        cmd = self.bot.get_command(command)

        if cmd is None:
            await ctx.send(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        entry = {
            'server_id': str(ctx.message.guild.id),
            'permissions': {cmd.qualified_name: None}
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send("I have just removed the custom permissions for {}!".format(cmd))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def prefix(self, ctx, *, prefix: str):
        """This command can be used to set a custom prefix per server

        EXAMPLE: !prefix $
        RESULT: You now need to call commands like: $help"""
        key = str(ctx.message.guild.id)
        if len(prefix.strip()) > 20:
            await ctx.send("Please keep prefixes under 20 characters")
            return
        if prefix.lower().strip() == "none":
            prefix = None

        entry = {
            'server_id': key,
            'prefix': prefix
        }

        self.bot.db.save('server_settings', entry)

        if prefix is None:
            fmt = "I have just cleared your custom prefix, the default prefix will have to be used now"
        else:
            fmt = "I have just updated the prefix for this server; you now need to call commands with `{0}`. " \
                  "For example, you can call this command again with {0}prefix".format(prefix)
        await ctx.send(fmt)

    @commands.group(aliases=['rule'], invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def rules(self, ctx, rule: int = None):
        """This command can be used to view the current rules on the server

        EXAMPLE: !rules 5
        RESULT: Rule 5 is printed"""
        rules = self.bot.db.load('server_settings', key=ctx.message.guild.id, pluck='rules')

        if rules is None:
            await ctx.send("This server currently has no rules on it! I see you like to live dangerously...")
            return

        if rule is None:
            try:
                pages = utils.Pages(self.bot, message=ctx.message, entries=rules, per_page=5)
                pages.title = "Rules for {}".format(ctx.message.guild.name)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))
        else:
            try:
                fmt = rules[rule - 1]
            except IndexError:
                await ctx.send("That rules does not exist.")
                return
            await ctx.send("Rule {}: \"{}\"".format(rule, fmt))

    @rules.command(name='add', aliases=['create'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def rules_add(self, ctx, *, rule: str):
        """Adds a rule to this server's rules

        EXAMPLE: !rules add No fun allowed in this server >:c
        RESULT: No more fun...unless they break the rules!"""
        key = str(ctx.message.guild.id)
        rules = self.bot.db.load('server_settings', key=key, pluck='rules') or []
        rules.append(rule)

        entry = {
            'server_id': key,
            'rules': rules
        }

        self.bot.db.save('server_settings', entry)

        await ctx.send("I have just saved your new rule, use the rules command to view this server's current rules")

    @rules.command(name='remove', aliases=['delete'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def rules_delete(self, ctx, rule: int):
        """Removes one of the rules from the list of this server's rules
        Provide a number to delete that rule

        EXAMPLE: !rules delete 5
        RESULT: Freedom from opression!"""
        key = str(ctx.message.guild.id)
        rules = self.bot.db.load('server_settings', key=key, pluck='rules') or []
        try:
            rules.pop(rule - 1)
            entry = {
                'server_id': key,
                'rules': rules
            }
            self.bot.db.save('server_settings', entry)
            await ctx.send("I have just removed that rule from your list of rules!")
        except IndexError:
            await ctx.send("That is not a valid rule number, try running the command again.")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def queuetype(self, ctx, new_type=None):
        """Switches the song queue type for music
        Choices are `user` or `song` queue
        The `user` queue rotates off of a wait list, where people join the waitlist and the next song in their
        playlist is the one that is played.

        The `song` queue rotates based on songs themselves, where people add a song to the server's playlist,
        and these are rotated through.

        EXAMPLE: !queuetype user
        RESULT: !queuetype """
        key = str(ctx.message.guild.id)

        if new_type is None:
            cur_type = self.bot.db.load('server_settings', key=key, pluck='queue_type') or 'song'
            await ctx.send("Current queue type is {}".format(cur_type))
            return

        new_type = new_type.lower().strip()
        if new_type not in ['user', 'song']:
            await ctx.send("Queue choices are either `user` or `song`. "
                           "Run `{}help queuetype` if you need more information".format(ctx.prefix))
        else:
            entry = {
                'server_id': key,
                'queue_type': new_type
            }
            self.bot.db.save('server_settings', entry)
            state = self.bot.get_cog('Music').voice_states.get(ctx.message.guild.id)
            if state:
                if new_type == "user" and not state.user_queue or new_type == "song" and state.user_queue:
                    state.switch_queue_type()
            await ctx.send("Current queue type is now `{}`".format(new_type))


def setup(bot):
    bot.add_cog(Administration(bot))
