from discord.ext import commands
from .utils import config
from .utils.config import getPhrase
from .utils import checks
import discord


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        boops = config.getContent('boops')
        if not boops.get(ctx.message.author.id):
            await self.bot.say(getPhrase("STATS:ERROR_NO_BOOPS").format(ctx.message.author.mention))
            return

        server_member_ids = [member.id for member in ctx.message.server.members]
        sorted_boops = sorted(boops.get(ctx.message.author.id).items(), key=lambda x: x[1], reverse=True)
        sorted_boops = [x for x in sorted_boops if x[0] in server_member_ids]

        most_boops = sorted_boops[0][1]
        most_id = sorted_boops[0][0]
        member = discord.utils.find(lambda m: m.id == most_id, self.bot.get_all_members())
        await self.bot.say(getPhrase("STATS:BOOP_COUNT").format(ctx.message.author.mention, member.mention, most_boops))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times"""
        boops = config.getContent('boops') or {}
        booped_members = boops.get(ctx.message.author.id)
        if booped_members is None:
            await self.bot.say(getPhrase("STATS:ERROR_NO_BOOPS").format(ctx.message.author.mention))
            return

        server_member_ids = [member.id for member in ctx.message.server.members]
        booped_members = {m_id: amt for m_id, amt in booped_members.items() if m_id in server_member_ids}

        output = "\n".join(
            getPhrase("STATS:GET_BOOP_INDIVIDUAL").format(discord.utils.get(self.bot.get_all_members(), id=m_id).display_name, amt) for
            m_id, amt in booped_members)
        await self.bot.say(getPhrase("STATS:GET_BOOP_LIST")+" ```\n{}```".format(output))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record"""
        battles = config.getContent('battle_records')

        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id: stats for member_id, stats in battles.items() if member_id in server_member_ids}
        sorted_members = sorted(server_members.items(), key=lambda k: k[1]['rating'], reverse=True)

        fmt = ""
        count = 1
        for x in sorted_members:
            member_id = x[0]
            stats = x[1]
            member = discord.utils.get(ctx.message.server.members, id=member_id)
            fmt += getPhrase("STATS:GET_LEADERBOARD_INDIVIDUAL").format(count, member.display_name, stats.get('rating'))+"\n"
            count += 1
        await self.bot.say(getPhrase("STATS:GET_LEADERBOARD")+" ```\n{}```".format(fmt))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def stats(self, ctx, member: discord.Member=None):
        """Prints the battling stats for you, or the user provided"""
        member = member or ctx.message.author

        all_members = config.getContent('battle_records')
        if member.id not in all_members:
            await self.bot.say(getPhrase("STATS:ERROR_NO_BATTLE_RECORD"))
            return

        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id: stats for member_id, stats in all_members.items() if
                          member_id in server_member_ids}
        sorted_server_members = sorted(server_members.items(), key=lambda x: x[1]['rating'], reverse=True)
        sorted_all_members = sorted(all_members.items(), key=lambda x: x[1]['rating'], reverse=True)

        server_rank = [i for i, x in enumerate(sorted_server_members) if x[0] == member.id][0] + 1
        total_rank = [i for i, x in enumerate(sorted_all_members) if x[0] == member.id][0] + 1
        rating = server_members[member.id]['rating']
        record = "{}-{}".format(server_members[member.id]['wins'], server_members[member.id]['losses'])
        getPhrase("STATS:GET_STATS").format(member.display_name, record, server_rank, len(server_members), total_rank, len(all_members),
                         rating)
        await self.bot.say('```\n{}```'.format(fmt))


def setup(bot):
    bot.add_cog(Stats(bot))
