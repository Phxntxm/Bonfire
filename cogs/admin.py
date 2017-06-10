from discord.ext import commands

from . import utils

import discord

import re

valid_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]


class Administration:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(enabled=False)
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    async def restrict(self, ctx, *options):
        """
        This is an intuitive command to restrict something to something
        The format is `!restrict what who/where`

        For example, `!restrict command role` will require a user to have `role`
        to be able to run `command`
        `!restrict command channel` will only allow `command` to be ran in `channel`
        """
        pass

    @commands.command(aliases=['nick'])
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
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

    @commands.command(aliases=['alerts'])
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def notifications(self, ctx, channel: discord.TextChannel):
        """This command is used to set a channel as the server's 'notifications' channel
        Any notifications (like someone going live on Twitch, or Picarto) will go to that channel

        EXAMPLE: !alerts #alerts
        RESULT: No more alerts spammed in #general!"""
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications_channel': str(channel.id)
        }

        self.bot.db.save('server_settings', entry)
        await ctx.send("I have just changed this server's 'notifications' channel"
                       "\nAll notifications will now go to `{}`".format(channel))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def usernotify(self, ctx, on_off: str):
        """This command can be used to set whether or not you want user notificaitons to show
        Provide on, yes, or true to set it on; otherwise it will be turned off

        EXAMPLE: !usernotify on
        RESULT: Annying join/leave notifications! Yay!"""
        # Join/Leave notifications can be kept separate from normal alerts
        # So we base this channel on it's own and not from alerts
        # When mod logging becomes available, that will be kept to it's own channel if wanted as well
        on_off = True if re.search("(on|yes|true)", on_off.lower()) else False

        entry = {
            'server_id': str(ctx.message.guild.id),
            'join_leave': on_off
        }

        self.bot.db.save('server_settings',entry)
        fmt = "notify" if on_off else "not notify"
        await ctx.send("This server will now {} if someone has joined or left".format(fmt))

    @commands.group()
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        # This command isn't meant to do anything, so just send an error if an invalid subcommand is passed
        pass

    @nsfw.command(name="add")
    @utils.custom_perms(kick_members=True)
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
