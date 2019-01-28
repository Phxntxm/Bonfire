import discord
from discord.ext import commands

import utils

import re


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def serverinfo(self, ctx):
        """Provides information about the server

        EXAMPLE: !serverinfo
        RESULT: Information about your server!"""
        server = ctx.message.guild
        # Create our embed that we'll use for the information
        embed = discord.Embed(title=server.name, description="Created on: {}".format(server.created_at.date()))

        # Make sure we only set the icon url if it has been set
        if server.icon_url != "":
            embed.set_thumbnail(url=server.icon_url)

        # Add our fields, these are self-explanatory
        embed.add_field(name='Region', value=str(server.region))
        embed.add_field(name='Total Emojis', value=len(server.emojis))

        # Get the amount of online members
        online_members = [m for m in server.members if str(m.status) == 'online']
        embed.add_field(name='Total members', value='{}/{}'.format(len(online_members), server.member_count))
        embed.add_field(name='Roles', value=len(server.roles))

        # Split channels into voice and text channels
        voice_channels = [c for c in server.channels if type(c) is discord.VoiceChannel]
        text_channels = [c for c in server.channels if type(c) is discord.TextChannel]
        embed.add_field(name='Channels', value='{} text, {} voice'.format(len(text_channels), len(voice_channels)))
        embed.add_field(name='Owner', value=server.owner.display_name)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def userinfo(self, ctx, *, user: discord.Member = None):
        """Provides information about a provided member

        EXAMPLE: !userinfo
        RESULT: Information about yourself!"""
        if user is None:
            user = ctx.message.author

        embed = discord.Embed(colour=user.colour)
        fmt = "{} ({})".format(str(user), user.id)
        embed.set_author(name=fmt, icon_url=user.avatar_url)

        embed.add_field(name='Joined this server', value=user.joined_at.date(), inline=False)
        embed.add_field(name='Joined Discord', value=user.created_at.date(), inline=False)

        # Sort them based on the hierarchy, but don't include @everyone
        roles = sorted([x for x in user.roles if not x.is_default()], reverse=True)
        # I only want the top 5 roles for this purpose
        roles = ", ".join("{}".format(x.name) for x in roles[:5])
        # If there are no roles, then just say this
        roles = roles or "No roles added"
        embed.add_field(name='Top 5 roles', value=roles, inline=False)

        # Add the activity if there is one
        act = user.activity
        if isinstance(act, discord.activity.Spotify):
            embed.add_field(name="Listening to", value=act.title, inline=False)
        elif isinstance(act, discord.activity.Game):
            embed.add_field(name='Playing', value=act.name, inline=False)
        await ctx.send(embed=embed)

    @commands.group()
    @utils.can_run(send_messages=True)
    async def command(self, ctx):
        pass

    @command.command(name="stats")
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def command_stats(self, ctx, *, command):
        """This command can be used to view some usage stats about a specific command

        EXAMPLE: !command stats play
        RESULT: The realization that this is the only reason people use me ;-;"""
        cmd = self.bot.get_command(command)
        if cmd is None:
            await ctx.send("`{}` is not a valid command".format(command))
            return

        command_stats = self.bot.db.load('command_usage', key=cmd.qualified_name)
        if command_stats is None:
            await ctx.send("That command has never been used! You know I worked hard on that! :c")
            return

        total_usage = command_stats['total_usage']
        member_usage = command_stats['member_usage'].get(str(ctx.message.author.id), 0)
        server_usage = command_stats['server_usage'].get(str(ctx.message.guild.id), 0)

        embed = discord.Embed(title="Usage stats for {}".format(cmd.qualified_name))
        embed.add_field(name="Total usage", value=total_usage, inline=False)
        embed.add_field(name="Your usage", value=member_usage, inline=False)
        embed.add_field(name="This server's usage", value=server_usage, inline=False)

        await ctx.send(embed=embed)

    @command.command(name="leaderboard")
    @utils.can_run(send_messages=True)
    async def command_leaderboard(self, ctx, option="server"):
        """This command can be used to print a leaderboard of commands
        Provide 'server' to print a leaderboard for this server
        Provide 'me' to print a leaderboard for your own usage

        EXAMPLE: !command leaderboard me
        RESULT: The realization of how little of a life you have"""
        if re.search('(author|me)', option):
            mid = str(ctx.message.author.id)
            # First lets get all the command usage
            command_stats = self.bot.db.load('command_usage')
            # Now use a dictionary comprehension to get just the command name, and usage
            # Based on the author's usage of the command

            stats = {
                command: data["member_usage"].get(mid)
                for command, data in command_stats.items()
                if data["member_usage"].get(mid, 0) > 0
            }
            # Now sort it by the amount of times used
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
            embed = discord.Embed(title="Your top 5 commands", colour=ctx.author.colour)
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

            for cmd, amount in sorted_stats:
                embed.add_field(name=cmd, value=amount, inline=False)

            await ctx.send(embed=embed)
        elif re.search('server', option):
            # This is exactly the same as above, except server usage instead of member usage
            sid = str(ctx.message.guild.id)
            command_stats = self.bot.db.load('command_usage')
            stats = {
                command: data['server_usage'].get(sid)
                for command, data in command_stats.items()
                if data.get("server_usage", {}).get(sid, 0) > 0
            }
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)[:5]
            embed = discord.Embed(title="The server's top 5 commands")
            embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)

            for cmd, amount in sorted_stats:
                embed.add_field(name=cmd, value=amount, inline=False)

            await ctx.send(embed=embed)

        else:
            await ctx.send("That is not a valid option, valid options are: `server` or `me`")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times

        EXAMPLE: !mostboops
        RESULT: You've booped @OtherPerson 351253897120935712093572193057310298 times!"""
        query = """
SELECT
    boopee, amount
FROM
    boops
WHERE
    booper=$1
AND
    boopee = ANY($2)
ORDER BY
    amount DESC
LIMIT 1
"""
        members = [m.id for m in ctx.guild.members]
        most = await self.bot.db.fetchrow(query, ctx.author.id, members)

        boops = self.bot.db.load('boops', key=ctx.message.author.id)
        if boops is None or "boops" not in boops:
            await ctx.send("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        if len(most) == 0:
            await ctx.send(f"You have not booped anyone in this server {ctx.author.mention}")
        else:
            member = ctx.guild.get_member(most['boopee'])
            await ctx.send(
                f"{ctx.author.mention} you have booped {member.display_name} the most amount of times, "
                f"coming in at {most['amount']} times"
            )

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times

        EXAMPLE: !listboops
        RESULT: The list of your booped members!"""

        query = """
SELECT
    boopee, amount
FROM
    boops
WHERE
    booper=$1
AND
    boopee = ANY($2)
ORDER BY
    amount DESC
LIMIT 10
        """

        members = [m.id for m in ctx.guild.members]
        most = await self.bot.db.fetch(query, ctx.author.id, members)

        if len(most) != 0:
            embed = discord.Embed(title="Your booped victims", colour=ctx.author.colour)
            embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)
            for row in most:
                member = ctx.guild.get_member(row['boopee'])
                embed.add_field(name=member.display_name, value=row['amount'])
            await ctx.send(embed=embed)
        else:
            await ctx.send("You haven't booped anyone in this server!")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record

        EXAMPLE: !leaderboard
        RESULT: A leaderboard of this server's battle records"""

        query = """
SELECT
    id, battle_rating
FROM
    users
WHERE
    id = any($1::bigint[])
ORDER BY
    battle_rating DESC
"""

        results = await self.bot.db.fetch(query, [m.id for m in ctx.guild.members])

        if len(results) == 0:
            await ctx.send("No one has battled on this server!")
        else:

            output = []
            for row in results:
                member = ctx.guild.get_member(row['id'])
                output.append(f"{member.display_name} (Rating: {row['battle_rating']})")

            try:
                pages = utils.Pages(ctx, entries=output)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def battlestats(self, ctx, member: discord.Member = None):
        """Prints the battling stats for you, or the user provided

        EXAMPLE: !stats @OtherPerson
        RESULT: How good they are at winning a completely luck based game"""
        member = member or ctx.message.author
        # Get the different data that we'll display
        server_rank = "{}/{}".format(*self.bot.br.get_server_rank(member))
        overall_rank = "{}/{}".format(*self.bot.br.get_rank(member))
        rating = self.bot.br.get_rating(member)
        record = self.bot.br.get_record(member)

        embed = discord.Embed(title="Battling stats for {}".format(ctx.author.display_name), colour=ctx.author.colour)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.add_field(name="Record", value=record, inline=False)
        embed.add_field(name="Server Rank", value=server_rank, inline=False)
        embed.add_field(name="Overall Rank", value=overall_rank, inline=False)
        embed.add_field(name="Rating", value=rating, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
