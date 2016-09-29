from discord.ext import commands
from .utils import config
from .utils import checks
import discord


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    def find_command(self, command):
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

    @commands.group(no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def command(self):
        pass

    @command.command(no_pm=True, name="stats")
    @checks.custom_perms(send_messages=True)
    async def command_stats(self, ctx, *, command):
        """This command can be used to view some usage stats about a specific command"""
        cmd = self.find_command(command)
        if cmd is None:
            await self.bot.say("`{}` is not a valid command".format(command))

        total_command_stats = await config.get('command_usage')

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        r_filter = {'member_id': ctx.message.author.id}
        boops = await config.get_content('boops', r_filter)
        if boops is None:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        # Just to make this easier, just pay attention to the boops data, now that we have the right entry
        boops = boops[0]['boops']

        # First get a list of the ID's of all members in this server, for use in list comprehension
        server_member_ids = [member.id for member in ctx.message.server.members]
        # Then get a sorted list, based on the amount of times they've booped the member
        # Reverse needs to be true, as we want it to go from highest to lowest
        sorted_boops = sorted(boops.items(), key=lambda x: x[1], reverse=True)
        # Then override the same list, checking if the member they've booped is in this server
        sorted_boops = [x for x in sorted_boops if x[0] in server_member_ids]

        # Since this is sorted, we just need to get the following information on the first user in the list
        most_id, most_boops = sorted_boops[0]

        member = discord.utils.find(lambda m: m.id == most_id, self.bot.get_all_members())
        await self.bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
            ctx.message.author.mention, member.mention, most_boops))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times"""
        r_filter = {'member_id': ctx.message.author.id}
        boops = await config.get_content('boops', r_filter)
        if boops is None:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        # Just to make this easier, just pay attention to the boops data, now that we have the right entry
        boops = boops[0]['boops']

        # Same concept as the mostboops method
        server_member_ids = [member.id for member in ctx.message.server.members]
        booped_members = {m_id: amt for m_id, amt in boops.items() if m_id in server_member_ids}
        sorted_booped_members = sorted(booped_members.items(), key=lambda k: k[1], reverse=True)

        output = "\n".join(
            "{0.display_name}: {1} times".format(discord.utils.get(ctx.message.server.members, id=m_id), amt) for
            m_id, amt in sorted_booped_members)
        await self.bot.say("You have booped:```\n{}```".format(output))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record"""
        # Create a list of the ID's of all members in this server, for comparison to the records saved
        server_member_ids = [member.id for member in ctx.message.server.members]
        r_filter = lambda row: row['member_id'] in server_member_ids
        battles = await config.get_content('battle_records', r_filter)

        # Sort the members based on their rating
        sorted_members = sorted(battles, key=lambda k: k['rating'], reverse=True)

        fmt = ""
        count = 1
        for x in sorted_members:
            member_id = x['member_id']
            rating = x['rating']
            member = ctx.message.server.get_member(member_id)
            fmt += "#{}) {} (Rating: {})\n".format(count, member.display_name, rating)
            count += 1
            if count >= 11:
                break
        await self.bot.say("Battling leaderboard for this server:```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def stats(self, ctx, member: discord.Member = None):
        """Prints the battling stats for you, or the user provided"""
        member = member or ctx.message.author

        # For this one, we don't want to pass a filter, as we do need all battle records
        # We need this because we want to make a comparison for overall rank
        all_members = await config.get_content('battle_records')

        # Make a list comprehension to just check if the user has battled
        if len([entry for entry in all_members if entry['member_id'] == member.id]) == 0:
            await self.bot.say("That user has not battled yet!")
            return

        # Same concept as the leaderboard
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {stats['member_id']: stats for stats in all_members if
                          stats['member_id'] in server_member_ids}
        sorted_server_members = sorted(server_members.items(), key=lambda x: x[1]['rating'], reverse=True)
        sorted_all_members = sorted(all_members.items(), key=lambda x: x[1]['rating'], reverse=True)

        # Enumurate the list so that we can go through, find the user's place in the list
        # and get just that for the rank
        server_rank = [i for i, x in enumerate(sorted_server_members) if x[0] == member.id][0] + 1
        total_rank = [i for i, x in enumerate(sorted_all_members) if x[0] == member.id][0] + 1
        # The rest of this is straight forward, just formatting
        rating = server_members[member.id]['rating']
        record = "{}-{}".format(server_members[member.id]['wins'], server_members[member.id]['losses'])
        fmt = 'Stats for {}:\n\tRecord: {}\n\tServer Rank: {}/{}\n\tOverall Rank: {}/{}\n\tRating: {}'
        fmt = fmt.format(member.display_name, record, server_rank, len(server_members), total_rank, len(all_members),
                         rating)
        await self.bot.say('```\n{}```'.format(fmt))


def setup(bot):
    bot.add_cog(Stats(bot))
