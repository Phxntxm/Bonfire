from discord.ext import commands

from . import utils

import discord
import re
import asyncio
import rethinkdb as r

valid_perms = [p for p in dir(discord.Permissions) if isinstance(getattr(discord.Permissions, p), property)]


class Mod:
    """Commands that can be used by a or an admin, depending on the command"""

    def __init__(self, bot):
        self.bot = bot

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
    @utils.custom_perms(kick_members=True)
    async def kick(self, ctx, member: discord.Member):
        """Used to kick a member from this server

        EXAMPLE: !kick @Member
        RESULT: They're kicked from the server?"""
        try:
            await member.kick()
            await ctx.send("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await ctx.send("But I can't, muh permissions >:c")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(ban_members=True)
    async def unban(self, ctx, member_id: int):
        """Used to unban a member from this server
        Due to the fact that I cannot find a user without being in a server with them
        only the ID should be provided

        EXAMPLE: !unban 353217589321750912
        RESULT: That dude be unbanned"""

        # Lets only accept an int for this method, in order to ensure only an ID is provided
        # Due to that though, we need to ensure a string is passed as the member's ID
        try:
            await self.bot.http.unban(member_id, ctx.guild.id)
            await ctx.send("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await ctx.send("But I can't, muh permissions >:c")
        except discord.HTTPException:
            await ctx.send("Sorry, I failed to unban that user!")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(ban_members=True)
    async def ban(self, ctx, *, member):
        """Used to ban a member
        This can be used to ban someone preemptively as well.
        Provide the ID of the user and this should ban them without them being in the server

        EXAMPLE: !ban 531251325312
        RESULT: That dude be banned"""

        # Lets first check if a user ID was provided, as that will be the easiest case to ban
        if member.isdigit():
            try:
                await self.bot.http.ban(member, ctx.guild.id)
                await ctx.send("\N{OK HAND SIGN}")
            except discord.Forbidden:
                await ctx.send("But I can't, muh permissions >:c")
            except discord.HTTPException:
                await ctx.send("Sorry, I failed to ban that user!")
            finally:
                return
        else:
            # If no ID was provided, lets try to convert what was given using the internal coverter
            converter = commands.converter.MemberConverter()
            converter.prepare(ctx, member)
            try:
                member = converter.convert()
            except commands.converter.BadArgument:
                await ctx.send(
                    '{} does not appear to be a valid member. If this member is not in this server, please provide '
                    'their ID'.format(member))
                return
        # Now lets try actually banning the member we've been given
        try:
            await member.ban()
            await ctx.send("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await ctx.send("But I can't, muh permissions >:c")
        except discord.HTTPException:
            await ctx.send("Sorry, I failed to ban that user!")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    async def ignore(self, ctx, member_or_channel):
        """This command can be used to have Bonfire ignore certain members/channels

        EXAMPLE: !ignore #general
        RESULT: Bonfire will ignore commands sent in the general channel"""
        key = str(ctx.message.guild.id)

        converter = commands.converter.MemberConverter()
        converter.prepare(ctx, member_or_channel)
        member = None
        channel = None
        try:
            member = converter.convert()
        except commands.converter.BadArgument:
            converter = commands.converter.TextChannelConverter()
            converter.prepare(ctx, member_or_channel)
            try:
                channel = converter.convert()
            except commands.converter.BadArgument:
                await ctx.send("{} does not appear to be a member or channel!".format(member_or_channel))
                return

        settings = await utils.get_content('server_settings', key)
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
        elif channel:
            if str(channel.id) in ignored['channels']:
                await ctx.send("I am already ignoring {}!".format(channel.mention))
                return
            else:
                ignored['channels'].append(str(channel.id))
                fmt = "Ignoring {}".format(channel.mention)

        update = {'ignored': ignored}
        await utils.update_content('server_settings', update, key)
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
        converter.prepare(ctx, member_or_channel)
        member = None
        channel = None
        try:
            member = converter.convert()
        except commands.converter.BadArgument:
            converter = commands.converter.TextChannelConverter()
            converter.prepare(ctx, member_or_channel)
            try:
                channel = converter.convert()
            except commands.converter.BadArgument:
                await ctx.send("{} does not appear to be a member or channel!".format(member_or_channel))
                return

        settings = await utils.get_content('server_settings', key)
        ignored = settings.get('ignored', {'members': [], 'channels': []})
        if member:
            if str(member.id) not in ignored['members']:
                await ctx.send("I'm not even ignoring {}!".format(member.display_name))
                return

            ignored['members'].remove(str(member.id))
            fmt = "I am no longer ignoring {}".format(member.display_name)
        elif channel:
            if str(channel.id) not in ignored['channels']:
                await ctx.send("I'm not even ignoring {}!".format(channel.mention))
                return

            ignored['channels'].remove(str(channel.id))
            fmt = "I am no longer ignoring {}".format(channel.mention)

        update = {'ignored': ignored}
        await utils.update_content('server_settings', update, key)
        await ctx.send(fmt)

    @commands.command(aliases=['alerts'])
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    async def notifications(self, ctx, channel: discord.TextChannel):
        """This command is used to set a channel as the server's 'notifications' channel
        Any notifications (like someone going live on Twitch, or Picarto) will go to that channel

        EXAMPLE: !alerts #alerts
        RESULT: No more alerts spammed in #general!"""
        key = str(ctx.message.guild.id)
        entry = {'server_id': key,
                 'notification_channel': str(channel.id)}
        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)
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
        key = str(ctx.message.guild.id)
        entry = {'server_id': key,
                 'join_leave': on_off}
        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)

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

        entry = {'server_id': key,
                 'nsfw_channels': [str(ctx.message.channel.id)]}
        update = {'nsfw_channels': r.row['nsfw_channels'].append(str(ctx.message.channel.id))}

        server_settings = await utils.get_content('server_settings', key)
        if server_settings and 'nsfw_channels' in server_settings.keys():
            await utils.update_content('server_settings', update, key)
        elif server_settings:
            await utils.update_content('server_settings', entry, key)
        else:
            await utils.add_content('server_settings', entry)

        await ctx.send("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")

    @nsfw.command(name="remove", aliases=["delete"])
    @utils.custom_perms(kick_members=True)
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel

        EXAMPLE: !nsfw remove
        RESULT: ;("""

        if type(ctx.message.channel) is discord.DMChannel:
            key = 'DMs'
        else:
            key = str(ctx.message.guild.id)

        server_settings = await utils.get_content('server_settings', key)
        channel = str(ctx.message.channel.id)
        try:
            channels = server_settings['nsfw_channels']
            if channel in channels:
                channels.remove(channel)

                entry = {'nsfw_channels': channels}
                await utils.update_content('server_settings', entry, key)
                await ctx.send("This channel has just been unregistered as a nsfw channel")
                return
        except (TypeError, IndexError):
            pass

        await ctx.send("This channel is not registered as a 'nsfw' channel!")

    @commands.command()
    @utils.custom_perms(kick_members=True)
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say

        EXAMPLE: !say I really like orange juice
        RESULT: I really like orange juice"""
        fmt = "\u200B{}".format(msg)
        await ctx.send(fmt)
        try:
            await ctx.message.delete()
        except:
            pass

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

        server_settings = await utils.get_content('server_settings', str(ctx.message.guild.id))
        try:
            server_perms = server_settings['permissions']
        except (TypeError, IndexError, KeyError):
            server_perms = {}

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

        key = str(ctx.message.guild.id)
        entry = {'server_id': key,
                 'permissions': {cmd.qualified_name: perm_value}}

        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)

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

        update = {'permissions': {cmd.qualified_name: None}}
        await utils.update_content('server_settings', update, str(ctx.message.guild.id))
        await ctx.send("I have just removed the custom permissions for {}!".format(cmd))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    async def prefix(self, ctx, *, prefix: str):
        """This command can be used to set a custom prefix per server

        EXAMPLE: !prefix new_prefix
        RESULT: You probably screwing it up and not realizing you now need to do new_prefixprefix"""
        key = str(ctx.message.guild.id)
        if len(prefix.strip()) > 20:
            await ctx.send("Please keep prefixes under 20 characters")
            return
        if prefix.lower().strip() == "none":
            prefix = None

        entry = {'server_id': key,
                 'prefix': prefix}

        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('prefixes', entry)

        if prefix is None:
            fmt = "I have just cleared your custom prefix, the default prefix will have to be used now"
        else:
            fmt = "I have just updated the prefix for this server; you now need to call commands with `{0}`. " \
                  "For example, you can call this command again with {0}prefix".format(prefix)
        await ctx.send(fmt)

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_messages=True)
    async def purge(self, ctx, limit: int = 100):
        """This command is used to a purge a number of messages from the channel

        EXAMPLE: !purge 50
        RESULT: -50 messages in this channel"""
        if not ctx.message.channel.permissions_for(ctx.message.guild.me).manage_messages:
            await ctx.send("I do not have permission to delete messages...")
            return
        try:
            await ctx.message.channel.purge(limit=limit, before=ctx.message)
            await ctx.message.delete()
        except discord.HTTPException:
            await ctx.message.channel.send("Detected messages that are too far "
                                           "back for me to delete; I can only bulk delete messages"
                                           " that are under 14 days old.")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(manage_messages=True)
    async def prune(self, ctx, *specifications=None):
        """This command can be used to prune messages from certain members
        Mention any user you want to prune messages from; if no members are mentioned, the messages removed will be mine
        If no limit is provided, then 100 will be used. This is also the max limit we can use

        EXAMPLE: !prune 50
        RESULT: 50 of my messages are removed from this channel"""
        # We can only get logs from 100 messages at a time, so make sure we are not above that threshold
        limit = 100
        for x in specifications:
            try:
                limit = int(limit)
                if limit <= 100:
                    break
                else:
                    limit = 100
            except (TypeError, ValueError):
                continue

        # If no members are provided, assume we're trying to prune our own messages
        members = ctx.message.mentions
        roles = ctx.message.role_mentions

        if len(members) == 0:
            members = [ctx.message.guild.me]

        # Our check for if a message should be deleted
        def check(m):
            if m.author in members:
                return True
            if any(x in m.author.roles for x in roles):
                return True
            return False

        # If we're not setting the user to the bot, then we're deleting someone elses messages
        # To do so, we need manage_messages permission, so check if we have that
        if not ctx.message.channel.permissions_for(ctx.message.guild.me).manage_messages:
            await ctx.send("I do not have permission to delete messages...")
            return

        # Since logs_from will give us any message, not just the user's we need
        # We'll increment count, and stop deleting messages if we hit the limit.
        count = 0
        async for msg in ctx.message.channel.history(before=ctx.message):
            if check(msg):
                try:
                    await msg.delete()
                    count += 1
                except:
                    pass
                if count >= limit:
                    break

        msg = await ctx.send("{} messages succesfully deleted".format(count))
        await asyncio.sleep(5)
        try:
            await msg.delete()
            await ctx.message.delete()
        except:
            pass

    @commands.group(aliases=['rule'], invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def rules(self, ctx, rule: int = None):
        """This command can be used to view the current rules on the server

        EXAMPLE: !rules 5
        RESULT: Rule 5 is printed"""
        server_settings = await utils.get_content('server_settings', str(ctx.message.guild.id))
        if server_settings is None:
            await ctx.send("This server currently has no rules on it! I see you like to live dangerously...")
            return

        rules = server_settings.get('rules')

        if not rules or len(rules) == 0:
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
        entry = {'server_id': key,
                 'rules': [rule]}
        update = {'rules': r.row['rules'].append(rule)}

        server_settings = await utils.get_content('server_settings', key)
        if server_settings and 'rules' in server_settings.keys():
            await utils.update_content('server_settings', update, key)
        elif server_settings:
            await utils.update_content('server_settings', entry, key)
        else:
            await utils.add_content('server_settings', entry)

        await ctx.send("I have just saved your new rule, use the rules command to view this server's current rules")

    @rules.command(name='remove', aliases=['delete'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    async def rules_delete(self, ctx, rule: int):
        """Removes one of the rules from the list of this server's rules
        Provide a number to delete that rule

        EXAMPLE: !rules delete 5
        RESULT: Freedom from opression!"""
        update = {'rules': r.row['rules'].delete_at(rule - 1)}
        if not await utils.update_content('server_settings', update, str(ctx.message.guild.id)):
            await ctx.send("That is not a valid rule number, try running the command again.")
        else:
            await ctx.send("I have just removed that rule from your list of rules!")


def setup(bot):
    bot.add_cog(Mod(bot))
