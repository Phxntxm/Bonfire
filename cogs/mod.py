from discord.ext import commands
from .utils import checks
from .utils import config

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

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def kick(self, ctx, member: discord.Member):
        """Used to kick a member from this server"""
        try:
            await self.bot.kick(member)
            await self.bot.say("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await self.bot.say("But I can't, muh permissions >:c")

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(ban_members=True)
    async def unban(self, ctx, member_id: int):
        """Used to unban a member from this server
        Due to the fact that I cannot find a user without being in a server with them
        only the ID should be provided"""

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
    @checks.custom_perms(ban_members=True)
    async def ban(self, ctx, *, member):
        """Used to ban a member
        This can be used to ban someone preemptively as well.
        Provide the ID of the user and this should ban them without them being in the server"""

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
                await self.bot.say("{} does not appear to be a valid member. If this member is not in this server, please provide their ID".format(member))
                return
        # Now lets try actually banning the member we've been given
        try:
            await self.bot.ban(member)
            await self.bot.say("\N{OK HAND SIGN}")
        except discord.HTTPException:
            await self.bot.say("Sorry, I failed to ban that user!")
        except discord.Forbidden:
            await self.bot.say("But I can't, muh permissions >:c")

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def alerts(self, ctx, channel: discord.Channel):
        """This command is used to set a channel as the server's 'notifications' channel
        Any notifications (like someone going live on Twitch, or Picarto) will go to that channel"""
        r_filter = {'server_id': ctx.message.server.id}
        entry = {'server_id': ctx.message.server.id,
                 'channel_id': channel.id}
        if not await config.add_content('server_alerts', entry, r_filter):
            await config.update_content('server_alerts', entry, r_filter)
        await self.bot.say("I have just changed this server's 'notifications' channel"
                           "\nAll notifications will now go to `{}`".format(channel))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def usernotify(self, ctx, on_off: str):
        """This command can be used to set whether or not you want user notificaitons to show
        This will save what channel you run this command in, that will be the channel used to send the notification to
        Provide on, yes, or true to set it on; otherwise it will be turned off"""
        # Join/Leave notifications can be kept separate from normal alerts
        # So we base this channel on it's own and not from alerts
        # When mod logging becomes available, that will be kept to it's own channel if wanted as well
        on_off = ctx.message.channel.id if re.search("(on|yes|true)", on_off.lower()) else None
        r_filter = {'server_id': ctx.message.server.id}
        entry = {'server_id': ctx.message.server.id,
                 'channel_id': on_off}
        if not await config.add_content('user_notifications', entry, r_filter):
            await config.update_content('user_notifications', entry, r_filter)
        fmt = "notify" if on_off else "not notify"
        await self.bot.say("This server will now {} if someone has joined or left".format(fmt))

    @commands.group(pass_context=True)
    async def nsfw(self, ctx):
        """Handles adding or removing a channel as a nsfw channel"""
        # This command isn't meant to do anything, so just send an error if an invalid subcommand is passed
        if ctx.invoked_subcommand is None:
            await self.bot.say('Invalid subcommand passed: {0.subcommand_passed}'.format(ctx))

    @nsfw.command(name="add", pass_context=True)
    @checks.custom_perms(kick_members=True)
    async def nsfw_add(self, ctx):
        """Registers this channel as a 'nsfw' channel"""
        r_filter = {'channel_id': ctx.message.channel.id}
        if await config.add_content('nsfw_channels', r_filter, r_filter):
            await self.bot.say("This channel has just been registered as 'nsfw'! Have fun you naughties ;)")
        else:
            await self.bot.say("This channel is already registered as 'nsfw'!")

    @nsfw.command(name="remove", aliases=["delete"], pass_context=True)
    @checks.custom_perms(kick_members=True)
    async def nsfw_remove(self, ctx):
        """Removes this channel as a 'nsfw' channel"""
        r_filter = {'channel_id': ctx.message.channel.id}
        if await config.remove_content('nsfw_channels', r_filter):
            await self.bot.say("This channel has just been unregistered as a nsfw channel")
        else:
            await self.bot.say("This channel is not registered as a ''nsfw' channel!")

    @commands.command(pass_context=True)
    @checks.custom_perms(kick_members=True)
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say"""
        fmt = "\u200B{}".format(msg)
        await self.bot.say(fmt)
        try:
            await self.bot.delete_message(ctx.message)
        except:
            pass

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def perms(self, ctx, *, command: str = None):
        """This command can be used to print the current allowed permissions on a specific command
        This supports groups as well as subcommands; pass no argument to print a list of available permissions"""
        if command is None:
            await self.bot.say(
                "Valid permissions are: ```\n{}```".format("\n".join("{}".format(i) for i in valid_perms)))
            return

        r_filter = {'server_id': ctx.message.server.id}
        server_perms = await config.get_content('custom_permissions', r_filter)
        try:
            server_perms = server_perms[0]
        except TypeError:
            server_perms = {}
        cmd = self.find_command(command)

        if cmd is None:
            await self.bot.say("That is not a valid command!")
            return

        perms_value = server_perms.get(cmd.qualified_name)
        if perms_value is None:
            # If we don't find custom permissions, get the required permission for a command
            # based on what we set in checks.custom_perms, if custom_perms isn't found, we'll get an IndexError
            try:
                custom_perms = [func for func in cmd.checks if "custom_perms" in func.__qualname__][0]
            except IndexError:
                # Loop through and check if there is a check called is_owner
                # If we loop through and don't find one, this means that the only other choice is to be
                # Able to manage the server (for the checks on perm commands)
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
        If you want to open the command to everyone, provide 'none' as the permission"""

        # Since subcommands exist, base the last word in the list as the permission, and the rest of it as the command
        command = " ".join(msg[0:len(msg) - 1])
        try:
            permissions = msg[len(msg) - 1]
        except IndexError:
            await self.bot.say("Please provide the permissions you want to setup, the format for this must be in:\n"
                               "`perms add <command> <permission>`")
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

        cmd = self.find_command(command)

        if cmd is None:
            await self.bot.say(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        # Two cases I use should never have custom permissions setup on them, is_owner for obvious reasons
        # The other case is if I'm using the default has_permissions case
        # Which means I do not want to check custom permissions at all
        # Currently the second case is only on adding and removing permissions, to avoid abuse on these
        for check in cmd.checks:
            if "is_owner" == check.__name__ or re.search("has_permissions", str(check)) is not None:
                await self.bot.say("This command cannot have custom permissions setup!")
                return

        r_filter = {'server_id': ctx.message.server.id}
        entry = {'server_id': ctx.message.server.id,
                 cmd.qualified_name: perm_value}

        # In all other cases, I've used add_content before update_content
        # In this case, I'm going the other way around, to make the least queries
        # As custom permissions are probably going to be ran multiple times per server
        # Whereas in most other cases, the command is probably going to be ran once/few times per server
        if not await config.update_content('custom_permissions', entry, r_filter):
            await config.add_content('custom_permissions', entry, r_filter)

        # Same case as prefixes, for now, trigger a manual update
        self.bot.loop.create_task(config.cache['custom_permissions'].update())
        await self.bot.say("I have just added your custom permissions; "
                           "you now need to have `{}` permissions to use the command `{}`".format(permissions, command))

    @perms.command(name="remove", aliases=["delete"], pass_context=True, no_pm=True)
    @commands.has_permissions(manage_server=True)
    async def remove_perms(self, ctx, *, command: str):
        """Removes the custom permissions setup on the command specified"""

        cmd = self.find_command(command)

        if cmd is None:
            await self.bot.say(
                "That command does not exist! You can't have custom permissions on a non-existant command....")
            return

        r_filter = {'server_id': ctx.message.server.id}
        await config.replace_content('custom_permissions', r.row.without(cmd.qualified_name), r_filter)
        await self.bot.say("I have just removed the custom permissions for {}!".format(cmd))

        # Same case as prefixes, for now, trigger a manual update
        self.bot.loop.create_task(config.cache['custom_permissions'].update())

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(manage_server=True)
    async def prefix(self, ctx, *, prefix: str):
        """This command can be used to set a custom prefix per server"""
        r_filter = {'server_id': ctx.message.server.id}
        if prefix.lower.strip() == "none":
            prefix = None

        entry = {'server_id': ctx.message.server.id,
                 'prefix': prefix}

        if not await config.add_content('prefixes', entry, r_filter):
            await config.update_content('prefixes', entry, r_filter)
        # For now, cache is not fully implemented, however is needed for prefixes
        # So we're going to manually trigger an update when this is ran
        self.bot.loop.create_task(config.cache['prefixes'].update())

        await self.bot.say(
            "I have just updated the prefix for this server; you now need to call commands with `{0}`."
            "For example, you can call this command again with {0}prefix".format(
                prefix))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(manage_messages=True)
    async def purge(self, ctx, limit: int = 100):
        """This command is used to a purge a number of messages from the channel"""
        if not ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
            await self.bot.say("I do not have permission to delete messages...")
            return
        await self.bot.purge_from(ctx.message.channel, limit=limit)

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(manage_messages=True)
    async def prune(self, ctx, limit: int = 100):
        """This command can be used to prune messages from certain members
        Mention any user you want to prune messages from; if no members are mentioned, the messages removed will be mine
        If no limit is provided, then 100 will be used. This is also the max limit we can use"""
        # We can only get logs from 100 messages at a time, so make sure we are not above that threshold
        if limit > 100:
            limit = 100

        # If no members are provided, assume we're trying to prune our own messages
        members = ctx.message.mentions
        if len(members) == 0:
            members = [ctx.message.server.me]
        # If we're not setting the user to the bot, then we're deleting someone elses messages
        # To do so, we need manage_messages permission, so check if we have that
        elif not ctx.message.channel.permissions_for(ctx.message.server.me).manage_messages:
            await self.bot.say("I do not have permission to delete messages...")
            return

        # Since logs_from will give us any message, not just the user's we need
        # We'll increment count, and stop deleting messages if we hit the limit.
        count = 0
        async for msg in self.bot.logs_from(ctx.message.channel):
            if msg.author in members:
                try:
                    await self.bot.delete_message(msg)
                    count += 1
                except discord.NotFound:
                    pass
                if count >= limit:
                    break
        msg = await self.bot.say("{} messages succesfully deleted".format(count))
        await asyncio.sleep(60)
        try:
            await self.bot.delete_message(msg)
        except discord.NotFound:
            pass

    @commands.group(aliases=['rule'], pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def rules(self, ctx, rule: int = None):
        """This command can be used to view the current rules on the server"""
        r_filter = {'server_id': ctx.message.server.id}
        rules = await config.get_content('rules', r_filter)
        try:
            rules = rules[0]['rules']
        except TypeError:
            await self.bot.say("This server currently has no rules on it! I see you like to live dangerously...")
            return
        if len(rules) == 0:
            await self.bot.say("This server currently has no rules on it! I see you like to live dangerously...")
            return

        if rule is None:
            # Enumerate the list, so that we can print the number and the rule for each rule
            fmt = "\n".join("{}) {}".format(num + 1, rule) for num, rule in enumerate(rules))
            await self.bot.say('```\n{}```'.format(fmt))
        else:
            try:
                fmt = rules[rule - 1]
            except IndexError:
                await self.bot.say("That rules does not exist.")
                return
            await self.bot.say("Rule {}: \"{}\"".format(rule, fmt))

    @rules.command(name='add', aliases=['create'], pass_context=True, no_pm=True)
    @checks.custom_perms(manage_server=True)
    async def rules_add(self, ctx, *, rule: str):
        """Adds a rule to this server's rules"""
        r_filter = {'server_id': ctx.message.server.id}
        entry = {'server_id': ctx.message.server.id,
                 'rules': [rule]}
        update = lambda row: row['rules'].append(rule)
        if not await config.update_content('rules', update, r_filter):
            await config.add_content('rules', entry, r_filter)

        await self.bot.say("I have just saved your new rule, use the rules command to view this server's current rules")

    @rules.command(name='remove', aliases=['delete'], pass_context=True, no_pm=True)
    @checks.custom_perms(manage_server=True)
    async def rules_delete(self, ctx, rule: int):
        """Removes one of the rules from the list of this server's rules
        Provide a number to delete that rule"""
        r_filter = {'server_id': ctx.message.server.id}
        update = {'rules': r.row['rules'].delete_at(rule - 1)}
        if not await config.update_content('rules', update, r_filter):
            await self.bot.say("That is not a valid rule number, try running the command again.")
        else:
            await self.bot.say("I have just removed that rule from your list of rules!")


def setup(bot):
    bot.add_cog(Mod(bot))
