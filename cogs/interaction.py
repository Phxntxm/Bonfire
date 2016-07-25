from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from .utils import config
from .utils import checks
import discord
import random


def battlingOff(player_id):
    battling = config.getContent('battling')
    
    battling = {p1:p2 for p1,p2 in battling.items() if not p2 == player_id and not p1 == player_id}
    
    config.saveContent('battling',battling)
                
    
def userBattling(ctx):
    battling = config.getContent('battling')
    if battling is None:
        return False
    if ctx.message.author.id in battling or ctx.message.author.id in battling.values():
        return True
    if str(ctx.command) == 'battle':
        return ctx.message.mentions[0].id in battling.values()
        
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
    
    winner_stats = {'wins':winner_wins,'losses':winner_losses,'rating':winner_rating}
    loser_stats = {'wins':loser_wins,'losses':loser_losses,'rating':loser_rating}
    battles[winner.id] = winner_stats
    battles[loser.id] = loser_stats
    
    return config.saveContent('battle_records', battles)


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True,invoke_without_command=True)
    @checks.customPermsOrRole("send_messages")
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
            
        battling = config.getContent('battling') or {}
        battling[ctx.message.author.id] = ctx.message.mentions[0].id
        config.saveContent('battling',battling)
        
        fmt = "{0.mention} has challenged you to a battle {1.mention}\n!accept or !decline"
        await self.bot.say(fmt.format(ctx.message.author, player2))
        config.loop.call_later(180,battlingOff,ctx.message.author.id)

    @battle.command(name="stats",pass_context=True)
    @checks.customPermsOrRole("send_messages")
    asynf def battle_stats(self, ctx, member: discord.Member=None)
        """Prints the stats for you, or the user provided"""
        member = member or ctx.message.author
        
        all_members = config.getContent('battle_records')
        server_member_ids = [member.id for member in ctx.message.server.members]
        server_members = {member_id:stats for member_id,stats in all_members.items() if member_id in server_member_ids}
        sorted_members = sorted(all_members.items(), key = lambda x: x[1]['rating'],reverse=True)
        
    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def accept(self, ctx):
        """Accepts the battle challenge"""
        if not userBattling(ctx):
            await self.bot.say("You are not currently in a battle!")
            return
            
        battling = config.getContent('battling') or {}
        p1 = [p1_id for p1_id,p2_id in battling.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say("You are not currently being challenged to a battle!")
            return
            
        battleP1 = discord.utils.find(lambda m: m.id == p1[0],ctx.message.server.members)
        battleP2 = ctx.message.author
        
        fmt = config.battleWins[random.randint(0, len(config.battleWins) - 1)]
        
        if random.randint(1, 100) < 50:
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            updateBattleRecords(battleP1, battleP2)
        else:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            updateBattleRecords(battleP2, battleP1)
        
        battlingOff(ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True)
    @checks.customPermsOrRole("send_messages")
    async def decline(self, ctx):
        """Declines the battle challenge"""
        if not userBattling(ctx):
            await self.bot.say("You are not currently in a battle!")
            return
            
        battling = config.getContent('battling') or {}
        p1 = [p1_id for p1_id,p2_id in battling.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say("You are not currently being challenged to a battle!")
            return
        battleP1 = discord.utils.find(lambda m: m.id == p1[0],ctx.message.server.members)
        battleP2 = ctx.message.author
        
        await self.bot.say("{0} has chickened out! {1} wins by default!".format(battleP2.mention, battleP1.mention))
        updateBattleRecords(battleP1, battleP2)
        battlingOff(ctx.message.author.id)

    @commands.command(pass_context=True, no_pm=True)
    @commands.cooldown(1,180,BucketType.user)
    @checks.customPermsOrRole("send_messages")
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

        if config.saveContent('boops', boops):
            fmt = "{0.mention} has just booped you {1.mention}! That's {2} times now!"
            await self.bot.say(fmt.format(booper, boopee, amount))
        else:
            await self.bot.say("I was unable to save this data")
            await self.bot.whisper("```{}```".format(boops))


def setup(bot):
    bot.add_cog(Interaction(bot))
