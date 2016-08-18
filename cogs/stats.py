from discord.ext import commands
from .utils import config
from .utils import checks
import discord


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        boops = config.get_content('boops') or {}
        if not boops.get(ctx.message.author.id):
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return
        
        # First get a list of the ID's of all members in this server, for use in list comprehension
        server_member_ids = [member.id for member in ctx.message.server.members]
        # Then get a sorted list, based on the amount of times they've booped the member
        # Reverse needs to be true, as we want it to go from highest to lowest
        sorted_boops = sorted(boops.get(ctx.message.author.id).items(), key=lambda x: x[1], reverse=True)
        # Then override the same list, checking if the member they've booped is in this server
        sorted_boops = [x for x in sorted_boops if x[0] in server_member_ids]
        
        # Since this is sorted, we just need to get the following information on the first user in the list
        most_boops = sorted_boops[0][1]
        most_id = sorted_boops[0][0]
        member = discord.utils.find(lambda m: m.id == most_id, self.bot.get_all_members())
        await self.bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
            ctx.message.author.mention, member.mention, most_boops))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times"""
        boops = config.get_content('boops') or {}
        booped_members = boops.get(ctx.message.author.id)
        if booped_members is None:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return
        
        # Same concept as the mostboops method
        server_member_ids = [member.id for member in ctx.message.server.members]
        booped_members = {m_id: amt for m_id, amt in booped_members.items() if m_id in server_member_ids}
        sorted_booped_members = sorted(booped_members.items(), key=lambda k: k[1], reverse=True)

        output = "\n".join(
            "{0.display_name}: {1} times".format(discord.utils.get(self.bot.get_all_members(), id=m_id), amt) for
            m_id, amt in sorted_booped_members.items())
        await self.bot.say("You have booped:```\n{}```".format(output))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record"""
        battles = config.get_content('battle_records') or {}
        
        # Same concept as mostboops
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id: stats for member_id, stats in battles.items() if member_id in server_member_ids}
        # Only real difference is the key, the key needs to be based on the rating in the member's dictionary of stats
        sorted_members = sorted(server_members.items(), key=lambda k: k[1]['rating'], reverse=True)

        fmt = ""
        count = 1
        for x in sorted_members:
            member_id = x[0]
            stats = x[1]
            member = discord.utils.get(ctx.message.server.members, id=member_id)
            fmt += "#{}) {} (Rating: {})\n".format(count, member.display_name, stats.get('rating'))
            count += 1
        await self.bot.say("Battling leaderboard for this server:```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def stats(self, ctx, member: discord.Member=None):
        """Prints the battling stats for you, or the user provided"""
        member = member or ctx.message.author

        all_members = config.get_content('battle_records') or {}
        if member.id not in all_members:
            await self.bot.say("That user has not battled yet!")
            return

        # Same concept as the leaderboard
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id: stats for member_id, stats in all_members.items() if
                          member_id in server_member_ids}
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
