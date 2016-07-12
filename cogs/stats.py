from discord.ext import commands
from discord.utils import find
from .utils import config
import re
import pymysql


class Stats:
    """Leaderboard/stats related commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def mostboops(self, ctx):
        """Shows the person you have 'booped' the most, as well as how many times"""
        try:
            cursor = config.getCursor()
            cursor.execute('use {0}'.format(config.db_boops))
            sql = "select id,amount from `{0}` where amount=(select MAX(amount) from `{0}`)"\
                .format(ctx.message.author.id)
            cursor.execute(sql)
            result = cursor.fetchone()
            member = find(lambda m: m.id == result.get('id'), self.bot.get_all_members())
            await self.bot.say("{0} you have booped {1} the most amount of times, coming in at {2} times".format(
                ctx.message.author.mention, member.mention, result.get('amount')))
            config.closeConnection()
        except pymysql.ProgrammingError:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))

    @commands.command(pass_context=True, no_pm=True)
    async def listboops(self, ctx):
        try:
            """Lists all the users you have booped and the amount of times"""
            members = ctx.message.server.members
            cursor = config.getCursor()
            cursor.execute('use {}'.format(config.db_boops))
            sql = "select * from `{}`".format(ctx.message.author.id)
            cursor.execute(sql)
            result = cursor.fetchall()
            if result is None:
                await self.bot.say("You have not booped anyone!")
                return
            output = "You have booped:"
            for r in result:
                member = find(lambda m: m.id == r['id'], self.bot.get_all_members())
                amount = r['amount']
                if member in members:
                    output += "\n{0.name}: {1} times".format(member, amount)
            config.closeConnection()
            await self.bot.say("```{}```".format(output))
        except pymysql.ProgrammingError:
            await self.bot.say("You have not booped anyone {} Why the heck not...?".format(ctx.message.author.mention))

    @commands.command(pass_context=True, no_pm=True)
    async def mostwins(self, ctx):
        """Prints a 'leaderboard' of everyone in the server's battling record"""
        try:
            members = ctx.message.server.members
            cursor = config.getCursor()
            cursor.execute('use {0}'.format(config.db_default))
            sql = "select * from battle_records"
            cursor.execute(sql)
            result = cursor.fetchall()
            count = 0
            fmt = []
            if result is not None:
                for r in result:
                    member = find(lambda m: m.id == r['id'], self.bot.get_all_members())
                    if member in members:
                        record = r['record']

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
            config.closeConnection()
            if len(fmt) == 0:
                await self.bot.say("```No battling records found from any members in this server```")
                return
            await self.bot.say("```{}```".format("\n".join(fmt)))
        except Exception as e:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(e).__name__, e))


def setup(bot):
    bot.add_cog(Stats(bot))
