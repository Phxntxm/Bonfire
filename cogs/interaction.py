from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from collections import defaultdict

import utils

import discord
import random
import functools

battle_outcomes = \
    ["A meteor fell on {loser}, {winner} is left standing and has been declared the victor!",
     "{loser} was shot through the heart, and {winner} is to blame",
     "{winner} has bucked {loser} into a tree, even Big Mac would be impressed at that kick!",
     "As they were battling, {loser} was struck by lightning! {winner} you lucked out this time!",
     "{loser} tried to dive at {winner} while fighting, somehow they missed and landed in quicksand."
     "Try paying more attention next time {loser}",
     "{loser} got a little...heated during the battle and ended up getting set on fire. "
     "{winner} wins by remaining cool",
     "Princess Celestia came in and banished {loser} to the moon. Good luck getting into any battles up there",
     "{loser} took an arrow to the knee, they are no longer an adventurer. Keep on adventuring {winner}",
     "Common sense should make it obvious not to get into battle with {winner}. Apparently {loser} didn't get the memo",
     "{winner} had a nice cup of tea with {loser} over their conflict, and mutually agreed that {winner} was Best Pony",
     "{winner} and {loser} had an intense staring contest. "
     "Sadly, {loser} forgot to breathe and lost much morethan the staring contest",
     "It appears {loser} is actually a pacifist, they ran away screaming and crying. "
     "Maybe you should have thought of that before getting in a fight?",
     "A bunch of parasprites came in and ate up the jetpack while {loser} was flying with it. Those pesky critters...",
     "{winner} used their charm to seduce {loser} to surrender.",
     "{loser} slipped on a banana peel and fell into a pit of spikes. That's actually impressive.",
     "{winner} realized it was high noon, {loser} never even saw it coming.",
     "{loser} spontaneously combusted...lol rip",
     "after many turns {winner} summons exodia and {loser} is sent to the shadow realm",
     "{winner} and {loser} sit down for an intense game of chess, "
     "in the heat of the moment {winner} forgot they were playing a "
     "game and summoned a real knight",
     "{winner} challenges {loser} to rock paper scissors, "
     "unfortunately for {loser}, {winner} chose scissors and stabbed them",
     "{winner} goes back in time and becomes {loser}'s best friend, winning without ever throwing a punch",
     "{loser} trips down some stairs on their way to the battle with {winner}",
     "{winner} books {loser} a one way ticket to Flugendorf prison",
     "{loser} was already dead",
     "{loser} was crushed under the weight of expectations",
     "{loser} was wearing a redshirt and it was their first day",
     "{winner} and {loser} were walking along when suddenly {loser} "
     "got kidnapped by a flying monkey; hope they had water with them",
     "{winner} brought an army to a fist fight, {loser} never saw their opponent once",
     "{winner} used multiple simultaneous devestating defensive deep strikes to overwhelm {loser}",
     "{winner} and {loser} engage in a dance off; {winner} wiped the floor with {loser}",
     "{loser} tried to hide in the sand to catch {winner} off guard, "
     "unfortunately looks like a Giant Antlion had the same "
     "idea for him",
     "{loser} was busy playing trash videogames the night before the fight and collapsed before {winner}",
     "{winner} threw a sick meme and {loser} totally got PRANK'D",
     "{winner} and {loser} go on a skiing trip together, turns out {loser} forgot how to pizza french-fry",
     "{winner} is the cure and {loser} is the disease....well {loser} was the disease",
     "{loser} talked their mouth off at {winner}...literally...",
     "Looks like {loser} didn't put enough points into kazoo playing, who knew they would have needed it",
     "{loser} was too scared by the illuminati and extra-dimensional talking horses to show up",
     "{loser} didn't press x enough to not die",
     "{winner} and {loser} go fishing to settle their debate, "
     "{winner} caught a sizeable fish and {loser} caught a boot older than time",
     "{winner} did a hero landing and {loser} was so surprised they gave up immediately"]

hugs = \
    ["*hugs {user}.*",
     "*tackles {user} for a hug.*",
     "*drags {user} into her dungeon where hugs ensue*",
     "*pulls {user} to the side for a warm hug*",
     "*goes out to buy a big enough blanket to embrace {user}*",
     "*hard codes an electric hug to {user}*",
     "*hires mercenaries to take {user} out....to a nice dinner*",
     "*pays $10 to not touch {user}*",
     "*clones herself to create a hug pile with {user}*",
     "*orders an airstrike of hugs {user}*",
     "*glomps {user}*",
     "*hears a knock at her door, opens it, finds {user} and hugs them excitedly*",
     "*goes in for a punch but misses and ends up hugging {user}*",
     "*hugs {user} from behind*",
     "*denies a hug from {user}*",
     "*does a hug to {user}*",
     "*lets {user} cuddle nonchalantly*",
     "*cuddles {user}*",
     "*burrows underground and pops up underneath {user} she hugs their legs.*",
     "*approaches {user} after having gone to the gym for several months and almost crushes them.*"]


class Interaction:
    """Commands that interact with another user"""

    def __init__(self, bot):
        self.bot = bot
        self.battles = defaultdict(list)

    def get_receivers_battle(self, receiver):
        for battle in self.battles.get(receiver.guild.id, []):
            if battle.is_receiver(receiver):
                return battle

    def can_initiate_battle(self, player):
        for battle in self.battles.get(player.guild.id, []):
            if battle.is_initiator(player):
                return False
        return True

    def can_receive_battle(self, player):
        for battle in self.battles.get(player.guild.id, []):
            if battle.is_receiver(player):
                return False
        return True

    def start_battle(self, initiator, receiver):
        battle = Battle(initiator, receiver)
        self.battles[initiator.guild.id].append(battle)
        return battle

    # Handles removing the author from the dictionary of battles
    def battling_off(self, battle):
        for guild, battles in self.battles.items():
            if battle in battles:
                battles.remove(battle)
                return

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def hug(self, ctx, user=None):
        """Makes me hug a person!

        EXAMPLE: !hug @Someone
        RESULT: I hug the shit out of that person"""
        if ctx.message.mention_everyone:
            await ctx.send("Your arms aren't big enough")
            return
        if user is None:
            user = ctx.author
        else:
            converter = commands.converter.MemberConverter()
            try:
                user = await converter.convert(ctx, user)
            except commands.converter.BadArgument:
                await ctx.send("Error: Could not find user: {}".format(user))
                return

        settings = await self.bot.db.fetchrow(
            "SELECT custom_hugs, include_default_hugs FROM guilds WHERE id = $1",
            ctx.guild.id
        )
        msgs = hugs.copy()
        if settings:
            custom_msgs = settings["custom_hugs"]
            default_on = settings["include_default_hugs"]
            if custom_msgs:
                if default_on or default_on is None:
                    msgs += custom_msgs
                else:
                    msgs = custom_msgs
        # Otherwise we simply just want to use the default, no matter what the default setting is

        fmt = random.SystemRandom().choice(msgs)
        await ctx.send(fmt.format(user=user.display_name))

    @commands.command(aliases=['1v1'])
    @commands.guild_only()
    @commands.cooldown(1, 20, BucketType.user)
    @utils.can_run(send_messages=True)
    async def battle(self, ctx, player2=None):
        """Challenges the mentioned user to a battle

        EXAMPLE: !battle @player2
        RESULT: A battle to the death"""
        # First check if everyone was mentioned
        if ctx.message.mention_everyone:
            await ctx.send("You want to battle {} people? Good luck with that...".format(
                len(ctx.channel.members) - 1)
            )
            return
        # Then check if nothing was provided
        if player2 is None:
            await ctx.send("Who are you trying to battle...?")
            return
        else:
            # Otherwise, try to convert to an actual member
            converter = commands.converter.MemberConverter()
            try:
                player2 = await converter.convert(ctx, player2)
            except commands.converter.BadArgument:
                await ctx.send("Error: Could not find user: {}".format(player2))
                return
        # Then check if the person used is the author
        if ctx.author.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("Why would you want to battle yourself? Suicide is not the answer")
            return
        # Check if the person battled is me
        if self.bot.user.id == player2.id:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("I always win, don't even try it.")
            return
        # Next two checks are to see if the author or person battled can be battled
        if not self.can_initiate_battle(ctx.author):
            ctx.command.reset_cooldown(ctx)
            await ctx.send("You are already battling someone!")
            return
        if not self.can_receive_battle(player2):
            ctx.command.reset_cooldown(ctx)
            await ctx.send("{} is already being challenged to a battle!".format(player2))
            return

        # Add the author and player provided in a new battle
        battle = self.start_battle(ctx.author, player2)

        fmt = f"{ctx.author.mention} has challenged you to a battle {player2.mention}\n" \
              f"{ctx.prefix}accept or {ctx.prefix}decline"
        # Add a call to turn off battling, if the battle is not accepted/declined in 3 minutes
        part = functools.partial(self.battling_off, battle)
        self.bot.loop.call_later(180, part)
        await ctx.send(fmt)

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def accept(self, ctx):
        """Accepts the battle challenge

        EXAMPLE: !accept
        RESULT: Hopefully the other person's death"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle
        battle = self.get_receivers_battle(ctx.author)
        if battle is None:
            await ctx.send("You are not currently being challenged to a battle!")
            return

        if ctx.guild.get_member(battle.initiator.id) is None:
            await ctx.send("The person who challenged you to a battle has apparently left the server....why?")
            self.battling_off(battle)
            return

        # Lets get the settings
        settings = await self.bot.db.fetchrow(
            "SELECT custom_battles, include_default_battles FROM guilds WHERE id = $1",
            ctx.guild.id
        )
        msgs = battle_outcomes
        if settings:
            custom_msgs = settings["custom_battles"]
            default_on = settings["include_default_battles"]
            # if they exist, then we want to see if we want to use default as well
            if custom_msgs:
                if default_on or default_on is None:
                    msgs += custom_msgs
                else:
                    msgs = custom_msgs

        fmt = random.SystemRandom().choice(msgs)
        # Due to our previous checks, the ID should only be in the dictionary once, in the current battle we're checking
        self.battling_off(battle)

        # Randomize the order of who is printed/sent to the update system
        winner, loser = battle.choose()

        member_list = [m.id for m in ctx.guild.members]
        query = """
SELECT id, rank, battle_rating, battle_wins, battle_losses
FROM
    (SELECT
        id,
        ROW_NUMBER () OVER (ORDER BY battle_rating DESC) as "rank",
        battle_rating,
        battle_wins,
        battle_losses
    FROM
        users
    WHERE
        id = any($1::bigint[]) AND
        battle_rating IS NOT NULL
    ) AS sub
WHERE id = any($2)
        """
        results = await self.bot.db.fetch(query, member_list, [winner.id, loser.id])

        old_winner = old_loser = None
        for result in results:
            if result['id'] == loser.id:
                old_loser = result
            else:
                old_winner = result

        winner_rating, loser_rating, = utils.update_rating(
            old_winner["battle_rating"] if old_winner else 1000,
            old_loser["battle_rating"] if old_loser else 1000,
        )

        update_query = """
UPDATE
    users
SET
    battle_rating = $1,
    battle_wins = $2,
    battle_losses = $3
WHERE
    id=$4
"""
        insert_query = """
INSERT INTO
    users (id, battle_rating,  battle_wins, battle_losses)
VALUES
    ($1, $2, $3, $4)
"""
        if old_loser:
            await self.bot.db.execute(
                update_query,
                loser_rating,
                old_loser['battle_wins'],
                old_loser['battle_losses'] + 1,
                loser.id
            )
        else:
            await self.bot.db.execute(insert_query, loser.id, loser_rating, 0, 1)
        if old_winner:
            await self.bot.db.execute(
                update_query,
                winner_rating,
                old_winner['battle_wins'] + 1,
                old_winner['battle_losses'] ,
                winner.id
            )
        else:
            await self.bot.db.execute(insert_query, winner.id, winner_rating, 1, 0)

        results = await self.bot.db.fetch(query, member_list, [winner.id, loser.id])

        new_winner_rank = new_loser_rank = None
        for result in results:
            if result['id'] == loser.id:
                new_loser_rank = result['rank']
            else:
                new_winner_rank = result['rank']

        fmt = fmt.format(winner=winner.display_name, loser=loser.display_name)
        if old_winner:
            fmt += "\n{} - Rank: {} ( +{} )".format(
                winner.display_name, new_winner_rank, old_winner["rank"] - new_winner_rank
            )
        else:
            fmt += "\n{} - Rank: {}".format(winner.display_name, new_winner_rank)
        if old_winner:
            fmt += "\n{} - Rank: {} ( -{} )".format(
                loser.display_name, new_loser_rank, new_loser_rank - old_winner["rank"]
            )
        else:
            fmt += "\n{} - Rank: {}".format(loser.display_name, new_loser_rank)

        await ctx.send(fmt)

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def decline(self, ctx):
        """Declines the battle challenge

        EXAMPLE: !decline
        RESULT: You chicken out"""
        # This is a check to make sure that the author is the one being BATTLED
        # And not the one that started the battle
        battle = self.get_receivers_battle(ctx.author)
        if battle is None:
            await ctx.send("You are not currently being challenged to a battle!")
            return

        self.battling_off(battle)
        await ctx.send("{} has chickened out! What a loser~".format(ctx.author.mention))

    @commands.command()
    @commands.guild_only()
    @commands.cooldown(1, 10, BucketType.user)
    @utils.can_run(send_messages=True)
    async def boop(self, ctx, boopee: discord.Member = None, *, message=""):
        """Boops the mentioned person

        EXAMPLE: !boop @OtherPerson
        RESULT: You do a boop o3o"""
        booper = ctx.author
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

        query = "SELECT amount FROM boops WHERE booper = $1 AND boopee = $2"
        amount = await self.bot.db.fetchrow(query, booper.id, boopee.id)
        if amount is None:
            amount = 1
            replacement_query = "INSERT INTO boops (booper, boopee, amount) VALUES($1, $2, $3)"
        else:
            replacement_query = "UPDATE boops SET amount=$3 WHERE booper=$1 AND boopee=$2"
            amount = amount['amount'] + 1

        await ctx.send(f"{booper.mention} has just booped {boopee.mention}{message}! That's {amount} times now!")
        await self.bot.db.execute(replacement_query, booper.id, boopee.id, amount)


class Battle:

    def __init__(self, initiator, receiver):
        self.initiator = initiator
        self.receiver = receiver
        self.rand = random.SystemRandom()

    def is_initiator(self, player):
        return player.id == self.initiator.id and player.guild.id == self.initiator.guild.id

    def is_receiver(self, player):
        return player.id == self.receiver.id and player.guild.id == self.receiver.guild.id

    def is_battling(self, player):
        return self.is_initiator(player) or self.is_receiver(player)

    def choose(self):
        """Returns the two users in the order winner, loser"""
        choices = [self.initiator, self.receiver]
        self.rand.shuffle(choices)
        return choices


def setup(bot):
    bot.add_cog(Interaction(bot))
