from discord.ext import commands
from .utils import checks
from .utils import config
from threading import Timer
import discord
import random

battling = False
battleP1 = None
battleP2 = None


def battlingOff():
    global battleP1
    global battleP2
    global battling
    battling = False
    battleP1 = ""
    battleP2 = ""


def updateBattleRecords(winner, loser):
    cursor = config.getCursor()
    cursor.execute('use {}'.format(config.db_default))

    # Update winners records
    sql = "select record from battle_records where id='{}'".format(winner.id)
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is not None:
        result = result['record'].split('-')
        result[0] = str(int(result[0]) + 1)
        sql = "update battle_records set record ='{}' where id='{}'".format("-".join(result), winner.id)
        cursor.execute(sql)
    else:
        sql = "insert into battle_records (id,record) values ('{}','1-0')".format(winner.id)
        cursor.execute(sql)

    # Update losers records
    sql = "select record from battle_records where id={0}".format(loser.id)
    cursor.execute(sql)
    result = cursor.fetchone()
    if result is not None:
        result = result['record'].split('-')
        result[1] = str(int(result[1]) + 1)
        sql = "update battle_records set record ='{0}' where id='{1}'".format('-'.join(result), loser.id)
        cursor.execute(sql)
    else:
        sql = "insert into battle_records (id,record) values ('{0}','0-1')".format(loser.id)
        cursor.execute(sql)

    config.closeConnection()


class Interaction:
    """Commands that interact with another user"""
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle"""
        global battleP1
        global battleP2
        global battling
        if battling:
            return
        if len(ctx.message.mentions) == 0:
            await self.bot.say("You must mention someone in the room " + ctx.message.author.mention + "!")
            return
        if len(ctx.message.mentions) > 1:
            await self.bot.say("You cannot battle more than one person at once!")
            return
        if ctx.message.author.id == player2.id:
            await self.bot.say("Why would you want to battle yourself? Suicide is not the answer")
            return
        if self.bot.user.id == player2.id:
            await self.bot.say("I always win, don't even try it.")
            return
        fmt = "{0.mention} has challenged you to a battle {1.mention}\n!accept or !decline"
        battleP1 = ctx.message.author
        battleP2 = player2
        await self.bot.say(fmt.format(ctx.message.author, player2))
        t = Timer(180, battlingOff)
        t.start()
        battling = True

    @commands.command(pass_context=True, no_pm=True)
    async def accept(self, ctx):
        """Accepts the battle challenge"""
        if not battling or battleP2 != ctx.message.author:
            return
        num = random.randint(1, 100)
        fmt = config.battleWins[random.randint(0, len(config.battleWins) - 1)]
        if num <= 50:
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            updateBattleRecords(battleP1, battleP2)
            battlingOff()
        elif num > 50:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            updateBattleRecords(battleP2, battleP1)
            battlingOff()
            
    @commands.command(pass_context=True, no_pm=True)
    async def decline(self, ctx):
        """Declines the battle challenge"""
        if not battling or battleP2 != ctx.message.author:
            return
        await self.bot.say("{0} has chickened out! {1} wins by default!".format(battleP2.mention, battleP1.mention))
        updateBattleRecords(battleP1, battleP2)
        battlingOff()
        
    @commands.command(pass_context=True, no_pm=True)
    async def boop(self, ctx, boopee: discord.Member):
        """Boops the mentioned person"""
        booper = ctx.message.author
        if len(ctx.message.mentions) == 0:
            await self.bot.say("You must mention someone in the room " + ctx.message.author.mention + "!")
            return
        if len(ctx.message.mentions) > 1:
            await self.bot.say("You cannot boop more than one person at once!")
            return
        if boopee.id == booper.id:
            await self.bot.say("You can't boop yourself! Silly...")
            return
        if boopee.id == self.bot.user.id:
            await self.bot.say("Why the heck are you booping me? Get away from me >:c")
            return

        cursor = config.getCursor()
        cursor.execute('use {0}'.format(config.db_boops))
        sql = "show tables like '" + str(booper.id) + "'"
        cursor.execute(sql)
        result = cursor.fetchone()
        amount = 1
        # Booper's table exists, continue
        if result is not None:
            sql = "select `amount` from `" + booper.id + "` where id='" + str(boopee.id) + "'"
            cursor.execute(sql)
            result = cursor.fetchone()
            # Boopee's entry exists, continue
            if result is not None:
                amount = result.get('amount') + 1
                sql = "update `" + str(booper.id) + "` set amount = " + str(amount) + " where id=" + str(
                    boopee.id)
                cursor.execute(sql)
            # Boopee does not exist, need to create the field for it
            else:
                sql = "insert into `" + str(booper.id) + "` (id,amount) values ('" + str(boopee.id) + "',1)"
                cursor.execute(sql)
        # Booper's table does not exist, need to create the table
        else:
            sql = "create table `" + str(booper.id) + \
                  "` (`id` varchar(255) not null,`amount` int(11) not null" + \
                  ",primary key (`id`)) engine=InnoDB default charset=utf8 collate=utf8_bin"
            cursor.execute(sql)
            sql = "insert into `" + str(booper.id) + "` (id,amount) values ('" + str(boopee.id) + "',1)"
            cursor.execute(sql)
        fmt = "{0.mention} has just booped you {1.mention}! That's {2} times now!"
        await self.bot.say(fmt.format(booper, boopee, amount))
        config.closeConnection()


def setup(bot):
    bot.add_cog(Interaction(bot))
