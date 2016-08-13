from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from .utils import config
from .utils import checks
from .utils.config import getPhrase
import discord
import random


def battlingOff(player_id):
    battling = config.getContent('battling')

    battling = {p1: p2 for p1, p2 in battling.items() if not p2 == player_id and not p1 == player_id}

    config.saveContent('battling', battling)


def userBattling(ctx):
    battling = config.getContent('battling')
    if battling is None:
        return False
    if ctx.message.author.id in battling.values() or ctx.message.author.id in battling.keys():
        return True
    if str(ctx.command) == 'battle':
        return ctx.message.mentions[0].id in battling.values() or ctx.message.mentions[0].id in battling.keys()

    return False


def updateBattleRecords(winner, loser):
    battles = config.getContent('battle_records')
    if battles is None:
        battles = {winner.id: "1-0", loser.id: "0-1"}

    winner_stats = battles.get(winner.id) or {}
    winner_rating = winner_stats.get('rating') or 1000

    loser_stats = battles.get(loser.id) or {}
    loser_rating = loser_stats.get('rating') or 1000

    difference = abs(winner_rating - loser_rating)
    rating_change = 0
    count = 25
    while count <= difference:
        if count > 300:
            break
        rating_change += 1
        count += 25

    if winner_rating > loser_rating:
        winner_rating += 16 - rating_change
        loser_rating -= 16 - rating_change
    else:
        winner_rating += 16 + rating_change
        loser_rating -= 16 + rating_change

    winner_wins = winner_stats.get('wins') or 0
    winner_losses = winner_stats.get('losses') or 0
    loser_wins = loser_stats.get('wins') or 0
    loser_losses = loser_stats.get('losses') or 0
    winner_wins += 1
    loser_losses += 1

    winner_stats = {'wins': winner_wins, 'losses': winner_losses, 'rating': winner_rating}
    loser_stats = {'wins': loser_wins, 'losses': loser_losses, 'rating': loser_rating}
    battles[winner.id] = winner_stats
    battles[loser.id] = loser_stats

    return config.saveContent('battle_records', battles)


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @commands.cooldown(1, 60, BucketType.user)
    @checks.customPermsOrRole(send_messages=True)
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle"""
        if len(ctx.message.mentions) == 0:
            await self.bot.say(getPhrase("INTERACTION:ERROR_NO_USER_MENTIONED").format(ctx.message.author.mention))
            return
        if len(ctx.message.mentions) > 1:
            await self.bot.say(getPhrase("INTERACTION:ERROR_MULTIPLE_MENTIONS").format(ctx.message.author.mention, getPhrase("INTERACTION:BATTLE")))
            return
        if ctx.message.author.id == player2.id:
            await self.bot.say(getPhrase("INTERACTION:ERROR_PREVENT_SUICIDE").format(ctx.message.author.mention))
            return
        if self.bot.user.id == player2.id:
            await self.bot.say(getPhrase("INTERACTION:ERROR_GODBOT").format(ctx.message.author.mention))
            return
        if userBattling(ctx):
            await self.bot.say(getPhrase("INTERACTION:ERROR_IN_BATTLE").format(ctx.message.author.mention, player2.mention))
            return

        battling = config.getContent('battling') or {}
        battling[ctx.message.author.id] = ctx.message.mentions[0].id
        config.saveContent('battling', battling)

        fmt = getPhrase("INTERACTION:BATTLE_REQUEST")
        config.loop.call_later(180, battlingOff, ctx.message.author.id)
        await self.bot.say(fmt.format(ctx.message.author, player2, config.commandPrefix))
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def accept(self, ctx):
        """Accepts the battle challenge"""
        if not userBattling(ctx):
            await self.bot.say(getPhrase("INTERACTION:ERROR_NOT_IN_BATTLE").format(ctx.message.author.mention))
            return

        battling = config.getContent('battling') or {}
        p1 = [p1_id for p1_id, p2_id in battling.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say(getPhrase("INTERACTION:ERROR_NO_BATTLE_REQUEST").format(ctx.message.author.mention))
            return

        battleP1 = discord.utils.find(lambda m: m.id == p1[0], ctx.message.server.members)
        battleP2 = ctx.message.author

        fmt = config.battleWins[random.randint(0, len(config.battleWins) - 1)]
        battlingOff(ctx.message.author.id)

        DarkscratchID = '106182485913690112'
        if battleP1.id == DarkscratchID:
            await self.bot.say(getPhrase("INTERACTION:BATTLE_GOOBORG_ALWAYS_WINS").format(battleP1.mention, battleP2.mention))
            updateBattleRecords(battleP1, battleP2)
        if battleP2.id == DarkscratchID:
            await self.bot.say(getPhrase("INTERACTION:BATTLE_GOOBORG_ALWAYS_WINS").format(battleP2.mention, battleP1.mention))
            updateBattleRecords(battleP2, battleP1)
        if random.randint(1, 100) < 50:
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            updateBattleRecords(battleP1, battleP2)
        else:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            updateBattleRecords(battleP2, battleP1)
        
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole(send_messages=True)
    async def decline(self, ctx):
        """Declines the battle challenge"""
        if not userBattling(ctx):
            await self.bot.say(getPhrase("INTERACTION:ERROR_NOT_IN_BATTLE").format(ctx.message.author.mention))
            return

        battling = config.getContent('battling') or {}
        p1 = [p1_id for p1_id, p2_id in battling.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say(getPhrase("INTERACTION:ERROR_NO_BATTLE_REQUEST").format(ctx.message.author.mention))
            return
        battleP1 = discord.utils.find(lambda m: m.id == p1[0], ctx.message.server.members)
        battleP2 = ctx.message.author

        battlingOff(ctx.message.author.id)
        await self.bot.say(getPhrase("INTERACTION:BATTLE_DECLINE").format(battleP2.mention, battleP1.mention))
        await self.bot.delete_message(ctx.message)

    @commands.command(pass_context=True, no_pm=True)
    @commands.cooldown(3, 30, BucketType.user)
    @checks.customPermsOrRole(send_messages=True)
    async def boop(self, ctx, boopee: discord.Member):
        """Boops the mentioned person"""
        booper = ctx.message.author
        if len(ctx.message.mentions) == 0:
            await self.bot.say(getPhrase("INTERACTION:ERROR_NO_USER_MENTIONED").format(ctx.message.author.mention))
            return
        if len(ctx.message.mentions) > 1:
            await self.bot.say(getPhrase("INTERACTION:ERROR_MULTIPLE_MENTIONS").format(ctx.message.author.mention, getPhrase("INTERACTION:BOOP")))
            return
        if boopee.id == booper.id:
            await self.bot.say(getPhrase("INTERACTION:ERROR_SELF_BOOP").format(ctx.message.author.mention))
            return
        if boopee.id == self.bot.user.id:
            await self.bot.say(getPhrase("INTERACTION:ERROR_BOT_BOOP").format(ctx.message.author.mention))
            return

        boops = config.getContent('boops') or {}

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

        config.saveContent('boops', boops)
        fmt = getPhrase("INTERACTION:BOOPED")
        await self.bot.say(fmt.format(booper, boopee, amount, "s" if amount > 1 else ""))
        await self.bot.delete_message(ctx.message)


def setup(bot):
    bot.add_cog(Interaction(bot))
