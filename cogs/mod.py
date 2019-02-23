from discord.ext import commands

import utils

import discord
import asyncio


class Moderation(commands.Cog):
    """Moderation commands, things that help control a server...but not the settings of the server"""

    @commands.command()
    @commands.guild_only()
    @utils.can_run(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        """Used to kick a member from this server

        EXAMPLE: !kick @Member
        RESULT: They're kicked from the server?"""
        try:
            await member.kick(reason=reason)
            await ctx.send("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await ctx.send("But I can't, muh permissions >:c")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(ban_members=True)
    async def unban(self, ctx, member_id: int):
        """Used to unban a member from this server
        Due to the fact that I cannot find a user without being in a server with them
        only the ID should be provided

        EXAMPLE: !unban 353217589321750912
        RESULT: That dude be unbanned"""

        # Lets only accept an int for this method, in order to ensure only an ID is provided
        # Due to that though, we need to ensure a string is passed as the member's ID
        try:
            await ctx.bot.http.unban(member_id, ctx.guild.id)
            await ctx.send("\N{OK HAND SIGN}")
        except discord.Forbidden:
            await ctx.send("But I can't, muh permissions >:c")
        except discord.HTTPException:
            await ctx.send("Sorry, I failed to unban that user!")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(ban_members=True)
    async def ban(self, ctx, member, *, reason=None):
        """Used to ban a member
        This can be used to ban someone preemptively as well.
        Provide the ID of the user and this should ban them without them being in the server

        EXAMPLE: !ban 531251325312
        RESULT: That dude be banned"""

        # Lets first check if a user ID was provided, as that will be the easiest case to ban
        if member.isdigit():
            try:
                await ctx.bot.http.ban(member, ctx.guild.id, reason=reason)
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
            try:
                member = await converter.convert(ctx, member)
            except commands.converter.BadArgument:
                await ctx.send(
                    '{} does not appear to be a valid member. If this member is not in this server, please provide '
                    'their ID'.format(member))
                return
            # Now lets try actually banning the member we've been given
            try:
                await member.ban(reason=reason)
                await ctx.send("\N{OK HAND SIGN}")
            except discord.Forbidden:
                await ctx.send("But I can't, muh permissions >:c")
            except discord.HTTPException:
                await ctx.send("Sorry, I failed to ban that user!")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_messages=True)
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
            try:
                await ctx.message.channel.send("Detected messages that are too far "
                                               "back for me to delete; I can only bulk delete messages"
                                               " that are under 14 days old.")
            except:
                pass

    @commands.command()
    @commands.guild_only()
    @utils.can_run(manage_messages=True)
    async def prune(self, ctx, *specifications):
        """This command can be used to prune messages from certain members
        Mention any user you want to prune messages from; if no members are mentioned, the messages removed will be mine
        If no limit is provided, then 100 will be used. This is also the max limit we can use

        EXAMPLE: !prune 50
        RESULT: 50 of my messages are removed from this channel"""
        # We can only get logs from 100 messages at a time, so make sure we are not above that threshold
        limit = 100
        for x in specifications:
            try:
                limit = int(x)
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
            if any(r in m.author.roles for r in roles):
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


def setup(bot):
    bot.add_cog(Moderation(bot))
