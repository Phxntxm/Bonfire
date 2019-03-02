import re
import utils
import discord
import datetime

from discord.ext import commands


class Stats(commands.Cog):
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    async def _get_guild_usage(self, guild):
        embed = discord.Embed(title="Server Command Usage")
        count = await self.bot.db.fetchrow("SELECT COUNT(*), MIN(executed) FROM command_usage WHERE guild=$1", guild.id)

        embed.description = f"{count[0]} total commands used"
        embed.set_footer(text='Tracking command usage since').timestamp = count[1] or datetime.datetime.utcnow()

        query = """
SELECT
    command, COUNT(*) as uses
FROM
    command_usage
WHERE
    guild = $1
GROUP BY
    command
ORDER BY
    "uses" DESC
LIMIT 5
        """

        results = await self.bot.db.fetch(query, guild.id)
        value = "\n".join(f"{command} ({uses} uses)" for command, uses in results or "No Commands")
        embed.add_field(name='Top Commands', value=value)

        return embed

    async def _get_member_usage(self, member):
        embed = discord.Embed(title=f"{member.display_name}'s command usage")
        count = await self.bot.db.fetchrow(
            "SELECT COUNT(*), MIN(executed) FROM command_usage WHERE author=$1",
            member.id
        )

        embed.description = f"{count[0]} total commands used"
        embed.set_footer(text='Tracking command usage since').timestamp = count[1] or datetime.datetime.utcnow()

        query = """
SELECT
    command, COUNT(*) as uses
FROM
    command_usage
WHERE
    author = $1
GROUP BY
    command
ORDER BY
    "uses" DESC
LIMIT 5
        """

        results = await self.bot.db.fetch(query, member.id)
        value = "\n".join(f"{command} ({uses} uses)" for command, uses in results or "No Commands")
        embed.add_field(name='Top Commands', value=value)

        return embed

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
    async def command_stats(self, ctx, *, member: discord.Member = None):
        """This command can be used to view some usage stats about commands from either a user, or the server. Provide
        a member if you want to view their usage, provide no one and the server's usage will be looked up"""

        if member is None:
            embed = await self._get_guild_usage(ctx.guild)
        else:
            embed = await self._get_member_usage(member)

        await ctx.send(embed=embed)

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
        most = await ctx.bot.db.fetchrow(query, ctx.author.id, members)

        if most is None or len(most) == 0:
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
        most = await ctx.bot.db.fetch(query, ctx.author.id, members)

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

        results = await ctx.bot.db.fetch(query, [m.id for m in ctx.guild.members])

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
        query = """
SELECT id, rank, battle_rating, battle_wins, battle_losses
FROM
    (SELECT
        id,
        ROW_NUMBER () OVER (ORDER BY battle_rating DESC) as "rank",
        battle_rating,
        battle_wins,
        battle_losses
    FROM
        users
    WHERE
        id = any($1::bigint[]) AND
        battle_rating IS NOT NULL
    ) AS sub
WHERE id = $2
        """
        member_list = [m.id for m in ctx.guild.members]
        result = await ctx.bot.db.fetchrow(query, member_list, member.id)
        server_rank = result["rank"]
        # overall_rank = "{}/{}".format(*ctx.bot.br.get_rank(member))
        rating = result["battle_rating"]
        record = f"{result['battle_wins']} - {result['battle_losses']}"

        embed = discord.Embed(title="Battling stats for {}".format(ctx.author.display_name), colour=ctx.author.colour)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        embed.add_field(name="Record", value=record, inline=False)
        embed.add_field(name="Server Rank", value=server_rank, inline=False)
        # embed.add_field(name="Overall Rank", value=overall_rank, inline=False)
        embed.add_field(name="Rating", value=rating, inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Stats(bot))
