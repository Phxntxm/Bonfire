from discord.ext import commands
from discord.utils import find
from .utils import config
from .utils import checks
import re
import pymysql


class Stats:
    """Leaderboard/stats related commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        try:
            boops = config.getContent('boops')
            if not boops.get(ctx.message.author.id):
                await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
                return
            
            most_boops = 0
            for b_id,amt in boops.get(ctx.message.author.id):
                if amt > most_boops:
                    most_boops = amt
                    most_id = b_id
            
            member = find(lambda m: m.id == b_id, self.bot.get_all_members())
            await self.bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
                ctx.message.author.mention, member.mention, most_boops))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def listboops(self, ctx):
        """Lists all the users you have booped and the amount of times"""
        members = ctx.message.server.members
        boops = config.getContent('boops')
        if boops is None or boops.get(ctx.message.author.id):
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
            return
        output = "You have booped:"
        for b_id,amt in boops.get(ctx.message.author.id):
            member = find(lambda m: m.id == b_id, self.bot.get_all_members())
            if member in members:
                output += "\n{0.name}: {1} times".format(member.name, amt)
        await self.bot.say("```{}```".format(output))

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def mostwins(self, ctx):
        """Prints a 'leaderboard' of everyone in the server's battling record"""
        members = ctx.message.server.members
        battles = config.getContent('battle_records')
        count = 0
        fmt = []
        if battles is not None:
            for m_id,record in battles:
                member = find(lambda m: m.id == m_id, self.bot.get_all_members())
                if member in members:
                    winAmt = int(record.split('-')[0])
                    loseAmt = int(record.split('-')[1])
                    percentage = winAmt / (winAmt + loseAmt)

                    position = count

                    indexPercentage = 0
                    if count > 0:
                        indexRecord = re.search('\d+-\d+', fmt[position - 1]).group(0)
                        indexWin = int(indexRecord.split('-')[0])
                        indexLose = int(indexRecord.split('-')[1])
                        indexPercentage = indexWin / (indexWin + indexLose)
                    while position > 0 and indexPercentage < percentage:
                        position -= 1
                        indexRecord = re.search('\d+-\d+', fmt[position - 1]).group(0)
                        indexWin = int(indexRecord.split('-')[0])
                        indexLose = int(indexRecord.split('-')[1])
                        indexPercentage = indexWin / (indexWin + indexLose)
                    fmt.insert(position, "{0} has a battling record of {1}".format(member.name, record))
                    count += 1
            for index in range(0, len(fmt)):
                fmt[index] = "{0}) {1}".format(index + 1, fmt[index])
        if len(fmt) == 0:
            await self.bot.say("```No battling records found from any members in this server```")
            return
        await self.bot.say("```{}```".format("\n".join(fmt)))


def setup(bot):
    bot.add_cog(Stats(bot))
