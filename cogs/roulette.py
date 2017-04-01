import discord
import random
import pendulum
import asyncio

from discord.ext import commands

from . import utils

class Roulette:

    def __init__(self, bot):
        self.bot = bot
        self.roulettes = []

    def get_game(self, server):
        for x in self.roulettes:
            if x.server == server:
                return x

    def start_game(self, server, time):
        game = self.get_game(server)
        if game:
            return False
        else:
            game = Game(server, time)
            self.roulettes.append(game)
            return game

    def end_game(self, server):
        game = self.get_game(server)
        member = game.choose()
        self.roulettes.remove(game)
        return member

    @commands.group(no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def roulette(self, ctx):
        """Joins the current running roulette

        EXAMPLE: !roulette
        RESULT: You're probably going to get kicked..."""
        r = self.get_game(ctx.message.guild)
        if not r:
            await ctx.send("There is no roulette game running on this server!")
        else:
            result = r.join(ctx.message.author)
            time_left = r.time_left
            if result:
                await ctx.send("You have joined this roulette game! Good luck~ This roulette will end in " + time_left)
            else:
                await ctx.send("This roulette will end in " + time_left)

    @roulette.command(name='start', aliases=['create'])
    @utils.custom_perms(kick_members=True)
    async def roulette_start(self, ctx, time: int=5):
        """Starts a roulette, that will end in one of the entrants being kicked from the server
        By default, the roulette will end in 5 minutes; provide a number (up to 30) to change how many minutes until it ends

        EXAMPLE: !roulette start
        RESULT: A new roulette game!"""
        if time < 1 or time > 30:
            await ctx.send("Invalid time! The roulette must be set to run between 1 and 30 minutes")
            return
        else:
            game = self.start_game(ctx.message.guild, time)
            if game:
                await ctx.send("A new roulette game has just started! A random entrant will be kicked in {} minutes."\
                               " Type {}roulette to join this roulette...good luck~".format(game.time_left, ctx.prefix))
            else:
                await ctx.send("There is already a roulette game running on this server!")
                return

        await asyncio.sleep(time * 60)
        member = self.end_game(ctx.message.guild)

        if member is None:
            await ctx.send("Well no one joined the roulette. That was boring.")
            return

        try:
            fmt = "The unlucky member to be kicked is {}; hopefully someone invites them back".format(member.display_name)
            await member.kick()
        except discord.Forbidden:
            fmt = "Well, the unlucky member chosen was {} but I can't kick you...so kick yourself please?".format(member.display_name)

        await ctx.send(fmt)


class Game:

    def __init__(self, guild, time):
        self.entrants = []
        self.server = guild
        self.end_time = pendulum.utcnow().add(minutes=time)

    @property
    def time_left(self):
        return (self.end_time - pendulum.utcnow()).in_words()

    def join(self, member):
        """Adds a member to the list of entrants"""
        if member in self.entrants:
            return False
        else:
            self.entrants.append(member)
            return True

    def choose(self):
        try:
            return random.SystemRandom().choice(self.entrants)
        except IndexError:
            return None

def setup(bot):
    bot.add_cog(Roulette(bot))
