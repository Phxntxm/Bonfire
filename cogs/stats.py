from discord.ext import commands
from .utils import config
from .utils import checks
import discord
import re
import operator


class Stats:
    """Leaderboard/stats related commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        boops = config.getContent('boops')
        members = ctx.message.server.members
        if not boops.get(ctx.message.author.id):
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return

        most_boops = 0
        for b_id, amt in boops.get(ctx.message.author.id).items():
            member = discord.utils.find(lambda m: m.id == b_id, self.bot.get_all_members())
            if member in members and amt > most_boops:
                most_boops = amt
                most_id = b_id

        member = discord.utils.find(lambda m: m.id == most_id, self.bot.get_all_members())
        await self.bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
            ctx.message.author.mention, member.mention, most_boops))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times"""
        members = ctx.message.server.members
        boops = config.getContent('boops')
        if boops is None or boops.get(ctx.message.author.id) is None:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return
        output = "You have booped:"
        for b_id, amt in boops.get(ctx.message.author.id).items():
            member = discord.utils.find(lambda m: m.id == b_id, self.bot.get_all_members())
            if member in members:
                output += "\n{0.name}: {1} times".format(member, amt)
        await self.bot.say("```{}```".format(output))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def leaderboard(self, ctx):
        """Prints a leaderboard of everyone in the server's battling record"""
        battles = config.getContent('battle_records')
        
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id:stats for member_id,stats in battles.items() if member_id in server_member_ids}
        sorted_members = sorted(server_members.items(), key = lambda x: x[1]['rating'],reverse=True)
        
        fmt = ""
        count = 1
        for x in sorted_members:
            member_id = x[0]
            stats = x[1]
            member = discord.utils.get(ctx.message.server.members,id=member_id)
            fmt += "#{}) {} (Rating: {})\n".format(count,member.display_name,stats.get('rating')) 
            count += 1
        await self.bot.say("```{}```".format(fmt))
        
    
    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    asynf def stats(self, ctx, member: discord.Member=None)
        """Prints the battling stats for you, or the user provided"""
        member = member or ctx.message.author
        
        all_members = config.getContent('battle_records')
        if not member in all_members:
            await self.bot.say("That user has not battled yet!")
            return
             
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id:stats for member_id,stats in all_members.items() if member_id in server_member_ids}
        sorted_server_members = sorted(server_members.items(), key = lambda x: x[1]['rating'],reverse=True)
        sorted_all_members = sorted(all_members.items(), key = lambda x: x[1]['rating'],reverse=True)
        
        server_rank = [i for i,x in enumerate(sorted_server_members) if x[0] == member.id][0]
        total_rank = [i for i,x in enumerate(sorted_all_members) if x[0] == member.id][0]
        rating = server_members[ctx.message.author.id]['rating']
        record = "{}-{}".format(server_members[member.id]['wins'],server_members[member.id]['losses'])
        fmt = 'Stats for {}:\n\tRecord: {}\n\tServer Rank: {}\n\tOverall Rank: {}\n\tRating: {}'
        .format(member.display_name,record,server_rank,total_rank,rating)

def setup(bot):
    bot.add_cog(Stats(bot))
