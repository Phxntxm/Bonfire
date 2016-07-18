from discord.ext import commands
from .utils import config
from .utils import checks
from threading import Timer
import discord
import random


def battlingOff(m_id):
    battling = config.getContent('battling')
    del battling[m_id]
    config.saveContent('battling',battling)
    
def userBattling(ctx):
    battling = config.getContent('battling')
    if battling is None:
        return False
    if ctx.message.author.id in battling:
        return True
    if str(ctx.command) == 'battle':
        return ctx.message.mentions[0].id in battling.values()
    return False


def updateBattleRecords(winner, loser):
    battles = config.getContent('battle_records')
    if battles is not None:
        record = battles.get(winner.id)
        if record is not None:
            record['wins'] = record['wins'] + 1
        else:
            record = {'wins':1,'losses':0}
        battles[winner.id] = record
        record = battles.get(loser.id)
        if record is not None:
            record['losses'] = record['losses'] + 1
        else:
            record = {'wins':0,'losses':1}
        battles[loser.id] = record
    else:
        battles = {winner.id: "1-0", loser.id: "0-1"}
    if config.saveContent('battle_records', battles):
        return True
    return False


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle"""
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
        if userBattling(ctx):
            await self.bot.say("You or the person you are trying to battle is already in a battle!")
            return
        fmt = "{0.mention} has challenged you to a battle {1.mention}\n!accept or !decline"
        battling = config.getContent('battling')
        if battling is None:
            battling = {}
        battling[ctx.message.author.id] = ctx.message.mentions[0].id
        config.saveContent('battling',battling)
        await self.bot.say(fmt.format(ctx.message.author, player2))
        t = Timer(180, battlingOff, ctx.message.author.id)
        t.start()

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def accept(self, ctx):
        """Accepts the battle challenge"""
        if not userBattling(ctx):
            return
        num = random.randint(1, 100)
        fmt = config.battleWins[random.randint(0, len(config.battleWins) - 1)]
        if num <= 50:
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            if not updateBattleRecords(battleP1, battleP2):
                await self.bot.say("I was unable to save this data")
            battlingOff(ctx.message.author.id)
        elif num > 50:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            if not updateBattleRecords(battleP2, battleP1):
                await self.bot.say("I was unable to save this data")
            battlingOff(ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def decline(self, ctx):
        """Declines the battle challenge"""
        if not userBattling(ctx):
            return
        await self.bot.say("{0} has chickened out! {1} wins by default!".format(battleP2.mention, battleP1.mention))
        if not updateBattleRecords(battleP1, battleP2):
            await self.bot.say("I was unable to save this data")
        battlingOff(ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
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

        boops = config.getContent('boops')
        if boops is None:
            boops = {}
        amount = 1
        booper_boops = boops.get(ctx.message.author.id)
        if booper_boops is None:
            boops[ctx.message.author.id] = {boopee.id: 1}
        elif booper_boops.get(boopee.id) is None:
            booper_boops[boopee.id] = 1
            boops[ctx.message.author.id] = booper_boops
        else:
            amount = booper_boops.get(boopee.id) + 1
            booper_boops[boopee.id] = amount
            boops[ctx.message.author.id] = booper_boops

        if config.saveContent('boops', boops):
            fmt = "{0.mention} has just booped you {1.mention}! That's {2} times now!"
            await self.bot.say(fmt.format(booper, boopee, amount))
        else:
            await self.bot.say("I was unable to save this data")


def setup(bot):
    bot.add_cog(Interaction(bot))
