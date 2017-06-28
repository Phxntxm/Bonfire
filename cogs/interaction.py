import rethinkdb as r
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from . import utils

import discord
import random
import functools
import asyncio

battle_outcomes = \
    ["A meteor fell on {1}, {0} is left standing and has been declared the victor!",
     "{1} was shot through the heart, and {0} is to blame",
     "{0} has bucked {1} into a tree, even Big Mac would be impressed at that kick!",
     "As they were battling, {1} was struck by lightning! {0} you lucked out this time!",
     "{1} tried to dive at {0} while fighting, somehow they missed and landed in quicksand."
     "Try paying more attention next time {1}",
     "{1} got a little...heated during the battle and ended up getting set on fire. {0} wins by remaining cool",
     "Princess Celestia came in and banished {1} to the moon. Good luck getting into any battles up there",
     "{1} took an arrow to the knee, they are no longer an adventurer. Keep on adventuring {0}",
     "Common sense should make it obvious not to get into battle with {0}. Apparently {1} didn't get the memo",
     "{0} had a nice cup of tea with {1} over their conflict, and mutually agreed that {0} was Best Pony",
     "{0} and {1} had an intense staring contest. "
     "Sadly, {1} forgot to breathe and lost much morethan the staring contest",
     "It appears {1} is actually a pacifist, they ran away screaming and crying. "
     "Maybe you should have thought of that before getting in a fight?",
     "A bunch of parasprites came in and ate up the jetpack while {1} was flying with it. Those pesky critters...",
     "{0} used their charm to seduce {1} to surrender.",
     "{1} slipped on a banana peel and fell into a pit of spikes. That's actually impressive.",
     "{0} realized it was high noon, {1} never even saw it coming.",
     "{1} spontaneously combusted...lol rip",
     "after many turns {0} summons exodia and {1} is sent to the shadow realm",
     "{0} and {1} sit down for an intense game of chess, in the heat of the moment {0} forgot they were playing a "
     "game and summoned a real knight",
     "{0} challenges {1} to rock paper scissors, unfortunately for {1}, {0} chose scissors and stabbed them",
     "{0} goes back in time and becomes {1}'s best friend, winning without ever throwing a punch",
     "{1} trips down some stairs on their way to the battle with {0}",
     "{0} books {1} a one way ticket to Flugendorf prison",
     "{1} was already dead",
     "{1} was crushed under the weight of expectations",
     "{1} was wearing a redshirt and it was their first day",
     "{0} and {1} were walking along when suddenly {1} got kidnapped by a flying monkey; hope they had water with them",
     "{0} brought an army to a fist fight, {1} never saw their opponent once",
     "{0} used multiple simultaneous devestating defensive deep strikes to overwhelm {1}",
     "{0} and {1} engage in a dance off; {0} wiped the floor with {1}",
     "{1} tried to hide in the sand to catch {0} off guard, unfortunately looks like a Giant Antlion had the same "
     "idea for him",
     "{1} was busy playing trash videogames the night before the fight and collapsed before {0}",
     "{0} threw a sick meme and {1} totally got PRANK'D",
     "{0} and {1} go on a skiing trip together, turns out {1} forgot how to pizza french-fry",
     "{0} is the cure and {1} is the disease....well {1} was the disease",
     "{1} talked their mouth off at {0}...literally...",
     "Looks like {1} didn't put enough points into kazoo playing, who knew they would have needed it",
     "{1} was too scared by the illuminati and extra-dimensional talking horses to show up",
     "{1} didn't press x enough to not die",
     "{0} and {1} go fishing to settle their debate, {0} caught a sizeable fish and {1} caught a boot older than time",
     "{0} did a hero landing and {1} was so surprised they gave up immediately"]

hugs = \
    ["*hugs {}.*",
     "*tackles {} for a hug.*",
     "*drags {} into her dungeon where hugs ensue*",
     "*pulls {} to the side for a warm hug*",
     "*goes out to buy a big enough blanket to embrace {}*",
     "*hard codes an electric hug to {}*",
     "*hires mercenaries to take {} out....to a nice dinner*",
     "*pays $10 to not touch {}*",
     "*clones herself to create a hug pile with {}*",
     "*orders an airstrike of hugs {}*",
     "*glomps {}*",
     "*hears a knock at her door, opens it, finds {} and hugs them excitedly*",
     "*goes in for a punch but misses and ends up hugging {}*",
     "*hugs {} from behind*",
     "*denies a hug from {}*",
     "*does a hug to {}*",
     "*lets {} cuddle nonchalantly*",
     "*cuddles {}*",
     "*burrows underground and pops up underneath {} she hugs their legs.*",
     "*approaches {} after having gone to the gym for several months and almost crushes them.*"]


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot
        self.battles = {}
        self.bot.br = BattleRankings(self.bot)
        self.bot.br.update_start()

    def get_battle(self, player):
        battles = self.battles.get(player.guild.id)

        if battles is None:
            return None

        for battle in battles:
            if battle['p2'] == player.id:
                return battle

    def can_battle(self, player):
        battles = self.battles.get(player.guild.id)

        if battles is None:
            return True

        for x in battles:
            if x['p1'] == player.id:
                return False
        return True

    def can_be_battled(self, player):
        battles = self.battles.get(player.guild.id)

        if battles is None:
            return True

        for x in battles:
            if x['p2'] == player.id:
                return False
        return True

    def start_battle(self, player1, player2):
        battles = self.battles.get(player1.guild.id, [])
        entry = {
            'p1': player1.id,
            'p2': player2.id
        }
        battles.append(entry)
        self.battles[player1.guild.id] = battles

    # Handles removing the author from the dictionary of battles
    def battling_off(self, player1=None, player2=None):
        if player1:
            guild = player1.guild.id
        else:
            guild = player2.guild.id
        battles = self.battles.get(guild, [])
        # Create a new list, exactly the way the last one was setup
        # But don't include the one start with player's ID
        new_battles = []
        for b in battles:
            if player1 and b['p1'] == player1.id:
                continue
            if player2 and b['p2'] == player2.id:
                continue
            new_battles.append(b)
        self.battles[guild] = new_battles

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def hug(self, ctx, user: discord.Member = None):
        """Makes me hug a person!

        EXAMPLE: !hug @Someone
        RESULT: I hug the shit out of that person"""
        if user is None:
            user = ctx.message.author

        fmt = random.SystemRandom().choice(hugs)
        await ctx.send(fmt.format(user.display_name))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 20, BucketType.user)
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle

        EXAMPLE: !battle @player2
        RESULT: A battle to the death"""
        if ctx.message.author.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Why would you want to battle yourself? Suicide is not the answer")
            return
        if self.bot.user.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("I always win, don't even try it.")
            return
        if not self.can_battle(ctx.message.author):
            ctx.command.reset_cooldown(ctx)
            await ctx.send("You are already battling someone!")
            return
        if not self.can_be_battled(player2):
            ctx.command.reset_cooldown(ctx)
            await ctx.send("{} is already being challenged to a battle!".format(player2))
            return

        # Add the author and player provided in a new battle
        self.start_battle(ctx.message.author, player2)

        fmt = "{0.message.author.mention} has challenged you to a battle {1.mention}\n" \
              "{0.prefix}accept or {0.prefix}decline"
        # Add a call to turn off battling, if the battle is not accepted/declined in 3 minutes
        part = functools.partial(self.battling_off, player1=ctx.message.author)
        self.bot.loop.call_later(180, part)
        await ctx.send(fmt.format(ctx, player2))

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def accept(self, ctx):
        """Accepts the battle challenge

        EXAMPLE: !accept
        RESULT: Hopefully the other person's death"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle
        battle = self.get_battle(ctx.message.author)
        if battle is None:
            await ctx.send("You are not currently being challenged to a battle!")
            return

        battleP1 = discord.utils.find(lambda m: m.id == battle['p1'], ctx.message.guild.members)
        if battleP1 is None:
            await ctx.send("The person who challenged you to a battle has apparently left the server....why?")
            return

        battleP2 = ctx.message.author

        # Get a random win message from our list
        fmt = random.SystemRandom().choice(battle_outcomes)
        # Due to our previous checks, the ID should only be in the dictionary once, in the current battle we're checking
        self.battling_off(player2=ctx.message.author)
        await self.bot.br.update()

        # Randomize the order of who is printed/sent to the update system
        if random.SystemRandom().randint(0, 1):
            winner = battleP1
            loser = battleP2
        else:
            winner = battleP2
            loser = battleP1

        msg = await ctx.send(fmt.format(winner.mention, loser.mention))
        old_winner_rank, _ = self.bot.br.get_server_rank(winner)
        old_loser_rank, _ = self.bot.br.get_server_rank(loser)

        # Update our records; this will update our cache
        await utils.update_records('battle_records', self.bot.db, winner, loser)
        # Now wait a couple seconds to ensure cache is updated
        await asyncio.sleep(2)
        await self.bot.br.update()

        # Now get the new ranks after this stuff has been updated
        new_winner_rank, _ = self.bot.br.get_server_rank(winner)
        new_loser_rank, _ = self.bot.br.get_server_rank(loser)
        fmt = msg.content
        fmt += "\n{} - Rank: {} ( +{} )".format(winner.display_name, new_winner_rank, old_winner_rank - new_winner_rank)
        fmt += "\n{} - Rank: {} ( -{} )".format(loser.display_name, new_loser_rank, new_loser_rank - old_loser_rank)

        try:
            await msg.edit(content=fmt)
        except:
            pass

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def decline(self, ctx):
        """Declines the battle challenge

        EXAMPLE: !decline
        RESULT: You chicken out"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle
        battle = self.get_battle(ctx.message.author)
        if battle is None:
            await ctx.send("You are not currently being challenged to a battle!")
            return

        battleP1 = discord.utils.find(lambda m: m.id == battle['p1'], ctx.message.guild.members)
        if battleP1 is None:
            await ctx.send("The person who challenged you to a battle has apparently left the server....why?")
            return

        battleP2 = ctx.message.author

        # There's no need to update the stats for the members if they declined the battle
        self.battling_off(player2=battleP2)
        await ctx.send("{} has chickened out! What a loser~".format(battleP2.mention))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, BucketType.user)
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def boop(self, ctx, boopee: discord.Member = None, *, message=""):
        """Boops the mentioned person

        EXAMPLE: !boop @OtherPerson
        RESULT: You do a boop o3o"""
        booper = ctx.message.author
        if boopee is None:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("You try to boop the air, the air boops back. Be afraid....")
            return
        # To keep formatting easier, keep it either "" or the message with a space in front
        if message is not None:
            message = " " + message
        if boopee.id == booper.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("You can't boop yourself! Silly...")
            return
        if boopee.id == self.bot.user.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Why the heck are you booping me? Get away from me >:c")
            return

        key = str(booper.id)
        boops = self.bot.db.load('boops', key=key, pluck='boops') or {}
        amount = boops.get(str(boopee.id), 0) + 1
        entry = {
            'member_id': str(booper.id),
            'boops': {
                str(boopee.id): amount
            }
        }
        self.bot.db.save('boops', entry)

        fmt = "{0.mention} has just booped {1.mention}{3}! That's {2} times now!"
        await ctx.send(fmt.format(booper, boopee, amount, message))


# noinspection PyMethodMayBeStatic
class BattleRankings:
    def __init__(self, bot):
        self.db = bot.db
        self.loop = bot.loop
        self.ratings = None

    def build_dict(self, seq, key):
        return dict((d[key], dict(d, rank=index + 1)) for (index, d) in enumerate(seq[::-1]))

    def update_start(self):
        self.loop.create_task(self.update())

    async def update(self):
        ratings = await self.db.query(r.table('battle_records').order_by('rating'))

        # Create a dictionary so that we have something to "get" from easily
        self.ratings = self.build_dict(ratings, 'member_id')

    def get(self, key):
        return self.ratings.get(str(key))

    def get_record(self, member):
        data = self.ratings.get(member.id, {})
        fmt = "{} - {}".format(data.get('wins'), data.get('losses'))
        return fmt

    def get_rating(self, member):
        data = self.ratings.get(member.id, {})
        return data.get('rating')

    def get_rank(self, member):
        data = self.ratings.get(member.id, {})
        return data.get('rank'), len(self.ratings)

    def get_server_rank(self, member):
        # Get the id's of all the members to compare to
        server_ids = [str(m.id) for m in member.guild.members]
        # Get all the ratings for members in this server
        ratings = [x for x in self.ratings.values() if x['member_id'] in server_ids]
        # Since we went from a dictionary to a list, we're no longer sorted, sort this
        ratings = sorted(ratings, key=lambda x: x['rating'])
        # Build our dictionary to get correct rankings
        server_ratings = self.build_dict(ratings, 'member_id')
        # Return the rank
        return server_ratings.get(str(member.id), {}).get('rank'), len(server_ratings)


def setup(bot):
    bot.add_cog(Interaction(bot))
