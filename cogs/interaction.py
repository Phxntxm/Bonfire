from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from .utils import config
from .utils import checks
import discord
import random


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot
        # Format for battles: {'serverid': {'player1': 'player2', 'player1': 'player2'}}
        self.battles = {}

    def user_battling(self, ctx, player2=None):
        battling = self.battles.get(ctx.message.server.id)

        # If no one is battling, obviously the user is not battling
        if battling is None:
            return False
        # Check if the author is battling
        if ctx.message.author.id in battling.values() or ctx.message.author.id in battling.keys():
            return True
        # Check if the player2 was provided, if they are check if they're in the list
        if player2 and (player2.id in battling.values() or player2.id in battling.keys()):
            return True
        # If neither are found, no one is battling
        return False

    # Handles removing the author from the dictionary of battles
    def battling_off(self, ctx):
        battles = self.battles.get(ctx.message.server.id) or {}
        player_id = ctx.message.author.id
        # Create a new dictionary, exactly the way the last one was setup
        # But don't include any that have the author's ID
        self.battles[ctx.message.server.id] = {p1: p2 for p1, p2 in battles.items() if
                                               not p2 == player_id and not p1 == player_id}

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True, enabled=False)
    @commands.cooldown(1, 180, BucketType.user)
    @checks.custom_perms(send_messages=True)
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle"""
        if ctx.message.author.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("Why would you want to battle yourself? Suicide is not the answer")
            return
        if self.bot.user.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("I always win, don't even try it.")
            return
        if self.user_battling(ctx, player2):
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("You or the person you are trying to battle is already in a battle!")
            return

        # Add the author and player provided in a new battle
        battles = self.battles.get(ctx.message.server.id) or {}
        battles[ctx.message.author.id] = player2.id
        self.battles[ctx.message.server.id] = battles

        fmt = "{0.mention} has challenged you to a battle {1.mention}\n!accept or !decline"
        # Add a call to turn off battling, if the battle is not accepted/declined in 3 minutes
        self.bot.loop.call_later(180, self.battling_off, ctx)
        await self.bot.say(fmt.format(ctx.message.author, player2))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def accept(self, ctx):
        """Accepts the battle challenge"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle 
        battles = self.battles.get(ctx.message.server.id) or {}
        p1 = [p1_id for p1_id, p2_id in battles.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say("You are not currently being challenged to a battle!")
            return

        battleP1 = discord.utils.find(lambda m: m.id == p1[0], ctx.message.server.members)
        battleP2 = ctx.message.author

        # Get a random win message from our list
        fmt = config.battle_wins[random.SystemRandom().randint(0, len(config.battle_wins) - 1)]
        # Due to our previous checks, the ID should only be in the dictionary once, in the current battle we're checking
        self.battling_off(ctx)

        # Randomize the order of who is printed/sent to the update system
        # All we need to do is change what order the challengers are printed/added as a paramater
        if random.SystemRandom().randint(0, 1):
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            await config.update_records('battle_records', battleP1, battleP2)
        else:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            await config.update_records('battle_records', battleP2, battleP1)

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def decline(self, ctx):
        """Declines the battle challenge"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle 
        battles = self.battles.get(ctx.message.server.id) or {}
        p1 = [p1_id for p1_id, p2_id in battles.items() if p2_id == ctx.message.author.id]
        if len(p1) == 0:
            await self.bot.say("You are not currently being challenged to a battle!")
            return

        battleP1 = discord.utils.find(lambda m: m.id == p1[0], ctx.message.server.members)
        battleP2 = ctx.message.author

        # There's no need to update the stats for the members if they declined the battle
        self.battling_off(ctx)
        await self.bot.say("{0} has chickened out! What a loser~".format(battleP2.mention, battleP1.mention))

    @commands.command(pass_context=True, no_pm=True)
    @commands.cooldown(1, 180, BucketType.user)
    @checks.custom_perms(send_messages=True)
    async def boop(self, ctx, boopee: discord.Member=None):
        """Boops the mentioned person"""
        booper = ctx.message.author
        if boopee is None:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("You try to boop the air, the air boops back. Be afraid....")
            return
        if boopee.id == booper.id:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("You can't boop yourself! Silly...")
            return
        if boopee.id == self.bot.user.id:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("Why the heck are you booping me? Get away from me >:c")
            return

        r_filter = {'member_id': booper.id}
        boops = await config.get_content('boops', r_filter)
        if boops is not None:
            boops = boops[0]['boops']
            # If the booper has never booped the member provided, assure it's 0
            amount = boops.get(boopee.id, 0) + 1
            boops[boopee.id] = amount

            await config.update_content('boops', {'boops': boops}, r_filter)
        else:
            entry = {'member_id': booper.id,
                     'boops': {boopee.id: 1}}

            await config.add_content('boops', entry, r_filter)
            amount = 1

        fmt = "{0.mention} has just booped you {1.mention}! That's {2} times now!"
        await self.bot.say(fmt.format(booper, boopee, amount))


def setup(bot):
    bot.add_cog(Interaction(bot))
