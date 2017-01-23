from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from .utils import config
from .utils import checks
from .utils import utilities
import discord
import random

battle_outcomes = \
    ["A meteor fell on {1}, {0} is left standing and has been declared the victor!",
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

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def hug(self, ctx, user: discord.Member = None):
        """Makes me hug a person!

        EXAMPLE: !hug @Someone
        RESULT: I hug the shit out of that person"""
        if user is None:
            user = ctx.message.author

        fmt = random.SystemRandom().choice(hugs)
        await self.bot.say(fmt.format(user.display_name))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def avatar(self, ctx, member: discord.Member = None):
        """Provides an image for the provided person's avatar (yours if no other member is provided)

        EXAMPLE: !avatar @person
        RESULT: A full image of that person's avatar"""

        if member is None:
            member = ctx.message.author

        url = member.avatar_url
        if ctx.message.server.me.permissions_in(ctx.message.channel).attach_files:
            file = await utilities.download_image(url)
            if file is None:
                await self.bot.say(url)
            else:
                await self.bot.upload(file, filename='avatar.jpg')
        else:
            await self.bot.say(url)

    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @commands.cooldown(1, 180, BucketType.user)
    @checks.custom_perms(send_messages=True)
    async def battle(self, ctx, player2: discord.Member):
        """Challenges the mentioned user to a battle

        EXAMPLE: !battle @player2
        RESULT: A battle to the death"""
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

        fmt = "{0.message.author.mention} has challenged you to a battle {1.mention}\n" \
              "{0.prefix}accept or {0.prefix}decline"
        # Add a call to turn off battling, if the battle is not accepted/declined in 3 minutes
        self.bot.loop.call_later(180, self.battling_off, ctx)
        await self.bot.say(fmt.format(ctx, player2))

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def accept(self, ctx):
        """Accepts the battle challenge

        EXAMPLE: !accept
        RESULT: Hopefully the other person's death"""
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
        fmt = random.SystemRandom().choice(battle_outcomes)
        # Due to our previous checks, the ID should only be in the dictionary once, in the current battle we're checking
        self.battling_off(ctx)

        # Randomize the order of who is printed/sent to the update system
        # All we need to do is change what order the challengers are printed/added as a paramater
        if random.SystemRandom().randint(0, 1):
            await self.bot.say(fmt.format(battleP1.mention, battleP2.mention))
            await utilities.update_records('battle_records', battleP1, battleP2)
        else:
            await self.bot.say(fmt.format(battleP2.mention, battleP1.mention))
            await utilities.update_records('battle_records', battleP2, battleP1)

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def decline(self, ctx):
        """Declines the battle challenge

        EXAMPLE: !decline
        RESULT: You chicken out"""
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
    async def boop(self, ctx, boopee: discord.Member = None, *, message = ""):
        """Boops the mentioned person

        EXAMPLE: !boop @OtherPerson
        RESULT: You do a boop o3o"""
        booper = ctx.message.author
        if boopee is None:
            ctx.command.reset_cooldown(ctx)
            await self.bot.say("You try to boop the air, the air boops back. Be afraid....")
            return
        # To keep formatting easier, keep it either "" or the message with a space in front
        if message is not None:
            message = " " + message
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

        fmt = "{0.mention} has just booped {1.mention}{3}! That's {2} times now!"
        await self.bot.say(fmt.format(booper, boopee, amount, message))


def setup(bot):
    bot.add_cog(Interaction(bot))
