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

    def find_command(self, command):
        # This method ensures the command given is valid. We need to loop through commands
        # As self.bot.commands only includes parent commands
        # So we are splitting the command in parts, looping through the commands
        # And getting the subcommand based on the next part
        # If we try to access commands of a command that isn't a group
        # We'll hit an AttributeError, meaning an invalid command was given
        # If we loop through and don't find anything, cmd will still be None
        # And we'll report an invalid was given as well
        cmd = None

        for part in command.split():
            try:
                if cmd is None:
                    cmd = self.bot.commands.get(part)
                else:
                    cmd = cmd.commands.get(part)
            except AttributeError:
                cmd = None
                break

        return cmd

    @commands.command(pass_context=True, no_pm=True, aliases=['nick'])
    @utils.custom_perms(kick_members=True)
    async def nickname(self, ctx, *, name=None):
        """Used to set the nickname for Bonfire (provide no nickname and it will reset)

        EXAMPLE: !nick Music Bot
        RESULT: My nickname is now music bot"""
        await self.bot.change_nickname(ctx.message.server.me, name)
        await self.bot.say("\N{OK HAND SIGN}")

    @commands.command(no_pm=True)
    @utils.custom_perms(kick_members=True)
    async def kick(self, member: discord.Member):
        """Used to kick a member from this server

        EXAMPLE: !kick @Member
        RESULT: They're kicked from the server?"""
        try:
            await self.bot.kick(member)
            await self.bot.say("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await self.bot.say("But I can't, muh permissions >:c")

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(ban_members=True)
    async def unban(self, ctx, member_id: int):
        """Used to unban a member from this server
        Due to the fact that I cannot find a user without being in a server with them
        only the ID should be provided

        EXAMPLE: !unban 353217589321750912
        RESULT: That dude be unbanned"""

        # Lets only accept an int for this method, in order to ensure only an ID is provided
        # Due to that though, we need to ensure a string is passed as the member's ID
        member = discord.Object(id=str(member_id))
        try:
            await self.bot.unban(ctx.message.server, member)
            await self.bot.say("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await self.bot.say("But I can't, muh permissions >:c")
        except discord.HTTPException:
            await self.bot.say("Sorry, I failed to unban that user!")

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(ban_members=True)
    async def ban(self, ctx, *, member):
        """Used to ban a member
        This can be used to ban someone preemptively as well.
        Provide the ID of the user and this should ban them without them being in the server

        EXAMPLE: !ban 531251325312
        RESULT: That dude be banned"""

        # Lets first check if a user ID was provided, as that will be the easiest case to ban
        if member.isdigit():
            # First convert it to a discord object based on the ID that was given
            member = discord.Object(id=member)
            # Next, to ban from the server the API takes a server obejct and uses that ID
            # So set "this" server as the member's server. This creates the "fake" member we need
            member.server = ctx.message.server
        else:
            # If no ID was provided, lets try to convert what was given using the internal coverter
            converter = commands.converter.UserConverter(ctx, member)
            try:
                member = converter.convert()
            except commands.converter.BadArgument:
                await self.bot.say(
                    '{} does not appear to be a valid member. If this member is not in this server, please provide '
                    'their ID'.format(member))
                return
        # Now lets try actually banning the member we've been given
        try:
            await self.bot.ban(member)
            await self.bot.say("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await self.bot.say("But I can't, muh permissions >:c")
        except discord.HTTPException:
            await self.bot.say("Sorry, I failed to ban that user!")

    @commands.command(no_pm=True, aliases=['alerts'], pass_context=True)
    @utils.custom_perms(kick_members=True)
    async def notifications(self, ctx, channel: discord.Channel):
        """This command is used to set a channel as the server's 'notifications' channel
        Any notifications (like someone going live on Twitch, or Picarto) will go to that channel
        EXAMPLE: !alerts #alerts
        RESULT: No more alerts spammed in #general!"""
        if str(channel.type) != "text":
            await self.bot.say("The notifications channel must be a text channel!")
            return

        key = ctx.message.server.id
        entry = {'server_id': key,
                 'notification_channel': channel.id}
        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)
        await self.bot.say("I have just changed this server's 'notifications' channel"
                           "\nAll notifications will now go to `{}`".format(channel))

    @commands.command(pass_context=True, no_pm=True)
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
        key = ctx.message.server.id
        entry = {'server_id': key,
                 'join_leave': on_off}
        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)

        fmt = "notify" if on_off else "not notify"
        await self.bot.say("This server will now {} if someone has joined or left".format(fmt))

    @commands.group(pass_context=True)
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        pass

    @nsfw.command(name="add", pass_context=True)
    @utils.custom_perms(kick_members=True)
    async def nsfw_add(self, ctx):
        """Registers this channel as a 'nsfw' channel
        EXAMPLE: !nsfw add
        RESULT: ;)"""
        key = ctx.message.server.id
        entry = {'server_id': key,
                 'nsfw_channels': [ctx.message.channel.id]}
        update = {'nsfw_channels': r.row['nsfw_channels'].append(ctx.message.channel.id)}

        server_settings = await utils.get_content('server_settings', key)
        if server_settings and 'nsfw_channels' in server_settings.keys():
            await utils.update_content('server_settings', update, key)
        elif server_settings:
            await utils.update_content('server_settings', entry, key)
        else:
            await utils.add_content('server_settings', entry)

        await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")

    @nsfw.command(name="remove", aliases=["delete"], pass_context=True)
    @utils.custom_perms(kick_members=True)
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel
        EXAMPLE: !nsfw remove
        RESULT: ;("""

        key = ctx.message.server.id
        server_settings = await utils.get_content('server_settings', key)
        channel = ctx.message.channel.id
        try:
            channels = server_settings['nsfw_channels']
            if channel in channels:
                channels.remove(channel)

                entry = {'nsfw_channels': channels}
                await utils.update_content('server_settings', entry, key)
                await self.bot.say("This channel has just been unregistered as a nsfw channel")
                return
        except (TypeError, IndexError):
            pass

        await self.bot.say("This channel is not registered as a 'nsfw' channel!")

    @commands.command(pass_context=True)
    @utils.custom_perms(kick_members=True)
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say

        EXAMPLE: !say I really like orange juice
        RESULT: I really like orange juice"""
        fmt = "\u200B{}".format(msg)
        await self.bot.say(fmt)
        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def perms(self, ctx, *, command: str = None):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions
        EXAMPLE: !perms help RESULT: Hopefully a result saying you just need send_messages permissions; otherwise lol
        this server's admin doesn't like me """
        if command is None:
            await self.bot.say(
                "Valid permissions are: ```\n{}```".format("\n".join("{}".format(i) for i in valid_perms)))
            return

        cmd = utils.find_command(self.bot, command)

        if cmd is None:
            await self.bot.say("That is not a valid command!")
            return

        server_settings = await utils.get_content('server_settings', ctx.message.server.id)
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
                        await self.bot.say("You need to own the bot to run this command")
                        return
                await self.bot.say(
                    "You are required to have `manage_server` permissions to run `{}`".format(cmd.qualified_name))
                return

            # Perms will be an attribute if custom_perms is found no matter what, so no need to check this
            perms = "\n".join(attribute for attribute, setting in custom_perms.perms.items() if setting)
            await self.bot.say(
                "You are required to have `{}` permissions to run `{}`".format(perms, cmd.qualified_name))
        else:
            # Permissions are saved as bit values, so create an object based on that value
            # Then check which permission is true, that is our required permission
            # There's no need to check for errors here, as we ensure a permission is valid when adding it
            permissions = discord.Permissions(perms_value)
            needed_perm = [perm[0] for perm in permissions if perm[1]][0]
            await self.bot.say("You need to have the permission `{}` "
                               "to use the command `{}` in this server".format(needed_perm, command))

    @perms.command(name="add", aliases=["setup,create"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def add_perms(self, ctx, *msg: str):
        """Sets up custom permissions on the provided command
        Format must be 'perms add <command> <permission>'
        If you want to open the command to everyone, provide 'none' as the permission
        EXAMPLE: !perms add skip ban_members
        RESULT: No more random people voting to skip a song"""

        # Since subcommands exist, base the last word in the list as the permission, and the rest of it as the command
        command = " ".join(msg[0:len(msg) - 1])
        try:
            permissions = msg[len(msg) - 1]
        except IndexError:
            await self.bot.say("Please provide the permissions you want to setup, the format for this must be in:\n"
                               "`perms add <command> <permission>`")
            return

        cmd = utils.find_command(self.bot, command)

        if cmd is None:
            await self.bot.say(
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
            await self.bot.say("{} does not appear to be a valid permission! Valid permissions are: ```\n{}```"
                               .format(permissions, "\n".join(valid_perms)))
            return
        perm_value = perm_obj.value

        # Two cases I use should never have custom permissions setup on them, is_owner for obvious reasons
        # The other case is if I'm using the default has_permissions case
        # Which means I do not want to check custom permissions at all
        # Currently the second case is only on adding and removing permissions, to avoid abuse on these
        for check in cmd.checks:
            if "is_owner" == check.__name__ or "has_permissions" in str(check):
                await self.bot.say("This command cannot have custom permissions setup!")
                return

        key = ctx.message.server.id
        entry = {'server_id': key,
                 'permissions': {cmd.qualified_name: perm_value}}

        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)

        await self.bot.say("I have just added your custom permissions; "
                           "you now need to have `{}` permissions to use the command `{}`".format(permissions, command))

    @perms.command(name="remove", aliases=["delete"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def remove_perms(self, ctx, *, command: str):
        """Removes the custom permissions setup on the command specified

        EXAMPLE: !perms remove play
        RESULT: Freedom!"""

        cmd = utils.find_command(self.bot, command)

        if cmd is None:
            await self.bot.say(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        update = {'permissions': {cmd.qualified_name: None}}
        await utils.update_content('server_settings', update, ctx.message.server.id)
        await self.bot.say("I have just removed the custom permissions for {}!".format(cmd))

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(manage_server=True)
    async def prefix(self, ctx, *, prefix: str):
        """This command can be used to set a custom prefix per server

        EXAMPLE: !prefix new_prefix
        RESULT: You probably screwing it up and not realizing you now need to do new_prefixprefix"""
        key = ctx.message.server.id
        if prefix.lower().strip() == "none":
            prefix = None

        entry = {'server_id': key,
                 'prefix': prefix}

        if not await utils.update_content('server_settings', entry, key):
            await utils.add_content('server_settings', entry)

        if prefix is None:
            fmt = "I have just cleared your custom prefix, the default prefix will have to be used now"
        else:
            fmt = "I have just updated the prefix for this server; you now need to call commands with `{0}`. " \
                  "For example, you can call this command again with {0}prefix".format(prefix)
        await self.bot.say(fmt)

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(manage_messages=True)
    async def purge(self, ctx, limit: int = 100):
        """This command is used to a purge a number of messages from the channel

        EXAMPLE: !purge 50
        RESULT: -50 messages in this channel"""
        if not ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
            await self.bot.say("I do not have permission to delete messages...")
            return
        try:
            await self.bot.purge_from(ctx.message.channel, limit=limit)
        except discord.HTTPException:
            await self.bot.send_message(ctx.message.channel, "Detected messages that are too far "
                                                             "back for me to delete; I can only bulk delete messages"
                                                             " that are under 14 days old.")

    @commands.command(pass_context=True, no_pm=True)
    @utils.custom_perms(manage_messages=True)
    async def prune(self, ctx, limit=None):
        """This command can be used to prune messages from certain members
        Mention any user you want to prune messages from; if no members are mentioned, the messages removed will be mine
        If no limit is provided, then 100 will be used. This is also the max limit we can use

        EXAMPLE: !prune 50
        RESULT: 50 of my messages are removed from this channel"""
        # We can only get logs from 100 messages at a time, so make sure we are not above that threshold
        try:
            # We may not have been passed a limit, and only mentions
            # If this happens, the limit will be set to that first mention
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 100

        if limit > 100:
            limit = 100
        if limit < 0:
            await self.bot.say("Limit cannot be less than 0!")
            return

        # If no members are provided, assume we're trying to prune our own messages
        members = ctx.message.mentions
        roles = ctx.message.role_mentions
        if len(members) == 0:
            members = [ctx.message.server.me]

        # Our check for if a message should be deleted
        def check(m):
            if m.author in members:
                return True
            if any(x in m.author.roles for x in roles):
                return True
            return False

        # If we're not setting the user to the bot, then we're deleting someone elses messages
        # To do so, we need manage_messages permission, so check if we have that
        if not ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
            await self.bot.say("I do not have permission to delete messages...")
            return

        # Since logs_from will give us any message, not just the user's we need
        # We'll increment count, and stop deleting messages if we hit the limit.
        count = 0
        async for msg in self.bot.logs_from(ctx.message.channel, before=ctx.message):
            if check(msg):
                try:
                    await self.bot.delete_message(msg)
                    count += 1
                except:
                    pass
                if count >= limit:
                    break
        msg = await self.bot.say("{} messages succesfully deleted".format(count))
        await asyncio.sleep(5)
        try:
            await self.bot.delete_message(msg)
            await self.bot.delete_message(ctx.message)
        except discord.NotFound:
            pass

    @commands.group(aliases=['rule'], pass_context=True, no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def rules(self, ctx, rule: int = None):
        """This command can be used to view the current rules on the server

        EXAMPLE: !rules 5
        RESULT: Rule 5 is printed"""
        server_settings = await utils.get_content('server_settings', ctx.message.server.id)
        rules = server_settings.get('rules')

        if not rules or len(rules) == 0:
            await self.bot.say("This server currently has no rules on it! I see you like to live dangerously...")
            return

        if rule is None:
            try:
                pages = utils.Pages(self.bot, message=ctx.message, entries=rules, per_page=5)
                pages.title = "Rules for {}".format(ctx.message.server.name)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await self.bot.say(str(e))
        else:
            try:
                fmt = rules[rule - 1]
            except IndexError:
                await self.bot.say("That rules does not exist.")
                return
            await self.bot.say("Rule {}: \"{}\"".format(rule, fmt))

    @rules.command(name='add', aliases=['create'], pass_context=True, no_pm=True)
    @utils.custom_perms(manage_server=True)
    async def rules_add(self, ctx, *, rule: str):
        """Adds a rule to this server's rules

        EXAMPLE: !rules add No fun allowed in this server >:c
        RESULT: No more fun...unless they break the rules!"""
        key = ctx.message.server.id
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

        await self.bot.say("I have just saved your new rule, use the rules command to view this server's current rules")

    @rules.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @utils.custom_perms(manage_server=True)
    async def rules_delete(self, ctx, rule: int):
        """Removes one of the rules from the list of this server's rules
        Provide a number to delete that rule

        EXAMPLE: !rules delete 5
        RESULT: Freedom from opression!"""
        update = {'rules': r.row['rules'].delete_at(rule - 1)}
        if not await utils.update_content('server_settings', update, ctx.message.server.id):
            await self.bot.say("That is not a valid rule number, try running the command again.")
        else:
            await self.bot.say("I have just removed that rule from your list of rules!")


def setup(bot):
    bot.add_cog(Mod(bot))
