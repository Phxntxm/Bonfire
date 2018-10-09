import discord
from discord.ext import commands

from . import utils

import re
import asyncio


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot
        self.donators = []
        self.bot.loop.create_task(self.donator_task())

    async def donator_task(self):
        while True:
            await self.get_donators()
            await asyncio.sleep(60)

    async def get_donators(self):
        # Set our base URL for the pagination task
        url = "https://api.patreon.com/oauth2/api/campaigns/{}/pledges".format(utils.patreon_id)
        # Set our headers with our bearer token
        headers = {'Authorization': 'Bearer {}'.format(utils.patreon_key)}
        # We need the names of all of them, and the names are embeded a bit so lets append while looping
        names = []
        # We need to page through, so lets create a loop and break when we find out we're done
        while True:
            # Simply get data based on the URL
            data = await utils.request(url, headers=headers, force_content_type_json=True)
            # First check if the data failed to retrieve, if so just return
            if data is None:
                return

            # Loop through the includes, as that's all we need
            for include in data['included']:
                # We only carry about the user's
                if include['type'] != 'user':
                    continue
                # This check checks the user's connected campaign (should only exist for *our* user) and checks if it
                #  matches
                if include.get('relationshipos', {}).get('campaign', {}).get('data', {}).get('id', {}) == str(
                        utils.patreon_id):
                    continue

                # Otherwise the only way this user was included, was if they are a patron, so include them
                name = include['attributes']['full_name']
                if name:
                    names.append(name)

            # Now, lets get our "next" link and request that
            url = data['links'].get('next')
            # If there is no None, that means there should only be a "first" and our pagination is done
            if url is None:
                break

        # Now just set the names
        self.donators = names

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
        await ctx.message.channel.trigger_typing()

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

        try:
            data = [("Command Name", cmd.qualified_name),
                    ("Total Usage", total_usage),
                    ("Your Usage", member_usage),
                    ("This Server's Usage", server_usage)]
            banner = await utils.create_banner(ctx.message.author, "Command Stats", data)
            await ctx.send(file=discord.File(banner, filename='banner.png'))
        except (FileNotFoundError, discord.Forbidden):
            fmt = "The command {} has been used a total of {} times\n" \
                  "{} times on this server\n" \
                  "It has been ran by you, {}, {} times".format(cmd.qualified_name, total_usage, server_usage,
                                                                ctx.message.author.display_name, member_usage)

            await ctx.send(fmt)

    @command.command(name="leaderboard")
    @utils.can_run(send_messages=True)
    async def command_leaderboard(self, ctx, option="server"):
        """This command can be used to print a leaderboard of commands
        Provide 'server' to print a leaderboard for this server
        Provide 'me' to print a leaderboard for your own usage

        EXAMPLE: !command leaderboard me
        RESULT: The realization of how little of a life you have"""
        await ctx.message.channel.trigger_typing()

        if re.search('(author|me)', option):
            author = ctx.message.author
            # First lets get all the command usage
            command_stats = self.bot.db.load('command_usage')
            # Now use a dictionary comprehension to get just the command name, and usage
            # Based on the author's usage of the command

            stats = {
                command: data["member_usage"].get(str(author.id))
                for command, data in command_stats.items()
                if data["member_usage"].get(str(author.id), 0) > 0
            }
            # Now sort it by the amount of times used
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

            # Create a string, each command on it's own line, based on the top 5 used commands
            # I'm letting it use the length of the sorted_stats[:5]
            # As this can include, for example, all 3 if there are only 3 entries
            try:
                top_5 = [(data[0], data[1]) for data in sorted_stats[:5]]
                banner = await utils.create_banner(ctx.message.author, "Your command usage", top_5)
                await ctx.send(file=discord.File(banner, filename='banner.png'))
            except (FileNotFoundError, discord.Forbidden):
                top_5 = "\n".join("{}: {}".format(data[0], data[1]) for data in sorted_stats[:5])
                await ctx.send(
                    "Your top {} most used commands are:\n```\n{}```".format(len(sorted_stats[:5]), top_5))
        elif re.search('server', option):
            # This is exactly the same as above, except server usage instead of member usage
            server = ctx.message.guild
            command_stats = self.bot.db.load('command_usage')
            stats = {
                command: data['server_usage'].get(str(server.id))
                for command, data in command_stats.items()
                if data.get("server_usage", {}).get(str(server.id), 0) > 0
            }
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
            try:
                top_5 = [(data[0], data[1]) for data in sorted_stats[:5]]
                banner = await utils.create_banner(ctx.message.author, "Server command usage", top_5)
                await ctx.send(file=discord.File(banner, filename='banner.png'))
            except (FileNotFoundError, discord.Forbidden):
                top_5 = "\n".join("{}: {}".format(data[0], data[1]) for data in sorted_stats[:5])
                await ctx.send(
                    "This server's top {} most used commands are:\n```\n{}```".format(len(sorted_stats[:5]), top_5))
        else:
            await ctx.send("That is not a valid option, valid options are: `server` or `me`")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times

        EXAMPLE: !mostboops
        RESULT: You've booped @OtherPerson 351253897120935712093572193057310298 times!"""
        boops = self.bot.db.load('boops', key=ctx.message.author.id)
        if boops is None:
            await ctx.send("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        # Just to make this easier, just pay attention to the boops data, now that we have the right entry
        boops = boops['boops']

        # First get a list of the ID's of all members in this server, for use in list comprehension
        server_member_ids = [str(member.id) for member in ctx.message.guild.members]
        # Then get a sorted list, based on the amount of times they've booped the member
        # Reverse needs to be true, as we want it to go from highest to lowest
        sorted_boops = sorted(boops.items(), key=lambda x: x[1], reverse=True)
        # Then override the same list, checking if the member they've booped is in this server
        sorted_boops = [x for x in sorted_boops if x[0] in server_member_ids]

        # Since this is sorted, we just need to get the following information on the first user in the list
        most_id, most_boops = sorted_boops[0]

        member = ctx.message.guild.get_member(int(most_id))

        await ctx.send("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
            ctx.message.author.mention, member.display_name, most_boops))

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times

        EXAMPLE: !listboops
        RESULT: The list of your booped members!"""
        await ctx.message.channel.trigger_typing()

        boops = self.bot.db.load('boops', key=ctx.message.author.id)
        if not boops:
            await ctx.send("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        # Just to make this easier, just pay attention to the boops data, now that we have the right entry
        boops = boops['boops']

        # Same concept as the mostboops method
        server_member_ids = [member.id for member in ctx.message.guild.members]
        booped_members = {int(m_id): amt for m_id, amt in boops.items() if int(m_id) in server_member_ids}
        sorted_booped_members = sorted(booped_members.items(), key=lambda k: k[1], reverse=True)
        # Now we only want the first 10 members, so splice this list
        sorted_booped_members = sorted_booped_members[:10]

        try:
            output = [("{0.display_name}".format(ctx.message.guild.get_member(m_id)), amt)
                      for m_id, amt in sorted_booped_members]
            banner = await utils.create_banner(ctx.message.author, "Your booped victims", output)
            await ctx.send(file=discord.File(banner, filename='banner.png'))
        except (FileNotFoundError, discord.Forbidden):
            output = "\n".join(
                "{0.display_name}: {1} times".format(ctx.message.guild.get_member(m_id), amt) for
                m_id, amt in sorted_booped_members)
            await ctx.send("You have booped:```\n{}```".format(output))

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record

        EXAMPLE: !leaderboard
        RESULT: A leaderboard of this server's battle records"""
        await ctx.message.channel.trigger_typing()

        # Create a list of the ID's of all members in this server, for comparison to the records saved
        server_member_ids = [member.id for member in ctx.message.guild.members]
        battles = self.bot.db.load('battle_records')
        if battles is None or len(battles) == 0:
            await ctx.send("No one has battled on this server!")

        battles = [
            battle
            for member_id, battle in battles.items()
            if int(member_id) in server_member_ids
        ]

        # Sort the members based on their rating
        sorted_members = sorted(battles, key=lambda k: k['rating'], reverse=True)

        output = []
        for x in sorted_members:
            member_id = int(x['member_id'])
            rating = x['rating']
            member = ctx.message.guild.get_member(member_id)
            output.append("{} (Rating: {})".format(member.display_name, rating))

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
        await ctx.message.channel.trigger_typing()

        member = member or ctx.message.author
        # Get the different data that we'll display
        server_rank = "{}/{}".format(*self.bot.br.get_server_rank(member))
        overall_rank = "{}/{}".format(*self.bot.br.get_rank(member))
        rating = self.bot.br.get_rating(member)
        record = self.bot.br.get_record(member)
        try:
            # Create our banner
            title = 'Stats for {}'.format(member.display_name)
            fmt = [('Record', record), ('Server Rank', server_rank), ('Overall Rank', overall_rank), ('Rating', rating)]
            banner = await utils.create_banner(member, title, fmt)
            await ctx.send(file=discord.File(banner, filename='banner.png'))
        except (FileNotFoundError, discord.Forbidden):
            fmt = 'Stats for {}:\n\tRecord: {}\n\tServer Rank: {}\n\tOverall Rank: {}\n\tRating: {}'
            fmt = fmt.format(member.display_name, record, server_rank, overall_rank, rating)
            await ctx.send('```\n{}```'.format(fmt))

    @commands.command(aliases=['donators'])
    @utils.can_run(send_messages=True)
    async def patrons(self, ctx):
        """Prints a list of all the patrons for Bonfire

        EXAMPLE: !donators
        RESULT: A list of the donators"""
        try:
            pages = utils.Pages(ctx, entries=self.donators)
            await pages.paginate()
        except utils.CannotPaginate as e:
            await ctx.send(str(e))


def setup(bot):
    bot.add_cog(Stats(bot))
