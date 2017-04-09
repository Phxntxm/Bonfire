import discord
from discord.ext import commands

from . import utils

import re


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
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

    @commands.group(pass_context=False)
    @utils.custom_perms(send_messages=True)
    async def command(self):
        pass

    @command.command(name="stats")
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def command_stats(self, ctx, *, command):
        """This command can be used to view some usage stats about a specific command

        EXAMPLE: !command stats play
        RESULT: The realization that this is the only reason people use me ;-;"""
        await ctx.message.channel.trigger_typing()

        cmd = self.bot.get_command(command)
        if cmd is None:
            await ctx.send("`{}` is not a valid command".format(command))
            return

        command_stats = await utils.get_content('command_usage', cmd.qualified_name)
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
            await ctx.send(file=banner)
        except (FileNotFoundError, discord.Forbidden):
            fmt = "The command {} has been used a total of {} times\n" \
                  "{} times on this server\n" \
                  "It has been ran by you, {}, {} times".format(cmd.qualified_name, total_usage, server_usage,
                                                                ctx.message.author.display_name, member_usage)

            await ctx.send(fmt)

    @command.command(name="leaderboard")
    @utils.custom_perms(send_messages=True)
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
            command_stats = await utils.get_content('command_usage')
            # Now use a dictionary comprehension to get just the command name, and usage
            # Based on the author's usage of the command
            stats = {data['command']: data['member_usage'].get(str(author.id)) for data in command_stats
                     if data['member_usage'].get(str(author.id), 0) > 0}
            # Now sort it by the amount of times used
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)

            # Create a string, each command on it's own line, based on the top 5 used commands
            # I'm letting it use the length of the sorted_stats[:5]
            # As this can include, for example, all 3 if there are only 3 entries
            try:
                top_5 = [(data[0], data[1]) for data in sorted_stats[:5]]
                banner = await utils.create_banner(ctx.message.author, "Your command usage", top_5)
                await ctx.send(file=banner)
            except (FileNotFoundError, discord.Forbidden):
                top_5 = "\n".join("{}: {}".format(data[0], data[1]) for data in sorted_stats[:5])
                await ctx.send(
                    "Your top {} most used commands are:\n```\n{}```".format(len(sorted_stats[:5]), top_5))
        elif re.search('server', option):
            # This is exactly the same as above, except server usage instead of member usage
            server = ctx.message.guild
            command_stats = await utils.get_content('command_usage')
            stats = {data['command']: data['server_usage'].get(str(server.id)) for data in command_stats
                     if data['server_usage'].get(str(server.id), 0) > 0}
            sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
            try:
                top_5 = [(data[0], data[1]) for data in sorted_stats[:5]]
                banner = await utils.create_banner(ctx.message.author, "Server command usage", top_5)
                await ctx.send(file=banner)
            except (FileNotFoundError, discord.Forbidden):
                top_5 = "\n".join("{}: {}".format(data[0], data[1]) for data in sorted_stats[:5])
                await ctx.send(
                    "This server's top {} most used commands are:\n```\n{}```".format(len(sorted_stats[:5]), top_5))
        else:
            await ctx.send("That is not a valid option, valid options are: `server` or `me`")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times

        EXAMPLE: !mostboops
        RESULT: You've booped @OtherPerson 351253897120935712093572193057310298 times!"""
        boops = await utils.get_content('boops', str(ctx.message.author.id))
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
    @utils.custom_perms(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times

        EXAMPLE: !listboops
        RESULT: The list of your booped members!"""
        await ctx.message.channel.trigger_typing()

        boops = await utils.get_content('boops', str(ctx.message.author.id))
        if boops is None:
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
            await ctx.send(file=banner)
        except (FileNotFoundError, discord.Forbidden):
            output = "\n".join(
                "{0.display_name}: {1} times".format(ctx.message.guild.get_member(m_id), amt) for
                m_id, amt in sorted_booped_members)
            await ctx.send("You have booped:```\n{}```".format(output))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record

        EXAMPLE: !leaderboard
        RESULT: A leaderboard of this server's battle records"""
        await ctx.message.channel.trigger_typing()

        # Create a list of the ID's of all members in this server, for comparison to the records saved
        server_member_ids = [member.id for member in ctx.message.guild.members]
        battles = await utils.get_content('battle_records')
        if battles is None or len(battles) == 0:
            await ctx.send("No one has battled on this server!")

        battles = [battle for battle in battles if int(battle['member_id']) in server_member_ids]

        # Sort the members based on their rating
        sorted_members = sorted(battles, key=lambda k: k['rating'], reverse=True)

        output = []
        for x in sorted_members:
            member_id = int(x['member_id'])
            rating = x['rating']
            member = ctx.message.guild.get_member(member_id)
            output.append("{} (Rating: {})".format(member.display_name, rating))

        try:
            pages = utils.Pages(self.bot, message=ctx.message, entries=output)
            await pages.paginate()
        except utils.CannotPaginate as e:
            await ctx.send(str(e))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def stats(self, ctx, member: discord.Member = None):
        """Prints the battling stats for you, or the user provided

        EXAMPLE: !stats @OtherPerson
        RESULT: How good they are at winning a completely luck based game"""
        await ctx.message.channel.trigger_typing()

        member = member or ctx.message.author

        # For this one, we don't want to pass a filter, as we do need all battle records
        # We need this because we want to make a comparison for overall rank
        all_members = await utils.get_content('battle_records')
        if all_members is None or len(all_members) == 0:
            await ctx.send("You have not battled anyone!")

        # Make a list comprehension to just check if the user has battled
        if len([entry for entry in all_members if entry['member_id'] == str(member.id)]) == 0:
            await ctx.send("That user has not battled yet!")
            return

        # Same concept as the leaderboard
        server_member_ids = [member.id for member in ctx.message.guild.members]
        server_members = [stats for stats in all_members if int(stats['member_id']) in server_member_ids]
        sorted_server_members = sorted(server_members, key=lambda x: x['rating'], reverse=True)
        sorted_all_members = sorted(all_members, key=lambda x: x['rating'], reverse=True)

        # Enumurate the list so that we can go through, find the user's place in the list
        # and get just that for the rank
        server_rank = [i for i, x in enumerate(sorted_server_members) if x['member_id'] == str(member.id)][0] + 1
        total_rank = [i for i, x in enumerate(sorted_all_members) if x['member_id'] == str(member.id)][0] + 1
        # The rest of this is straight forward, just formatting

        entry = [m for m in server_members if m['member_id'] == str(member.id)][0]
        rating = entry['rating']
        record = "{}-{}".format(entry['wins'], entry['losses'])
        try:
            title = 'Stats for {}'.format(member.display_name)
            fmt = [('Record', record), ('Server Rank', '{}/{}'.format(server_rank, len(server_members))),
                   ('Overall Rank', '{}/{}'.format(total_rank, len(all_members))), ('Rating', rating)]
            banner = await utils.create_banner(member, title, fmt)
            await ctx.send(file=banner)
        except (FileNotFoundError, discord.Forbidden):
            fmt = 'Stats for {}:\n\tRecord: {}\n\tServer Rank: {}/{}\n\tOverall Rank: {}/{}\n\tRating: {}'
            fmt = fmt.format(member.display_name, record, server_rank, len(server_members), total_rank,
                             len(all_members), rating)
            await ctx.send('```\n{}```'.format(fmt))


def setup(bot):
    bot.add_cog(Stats(bot))
