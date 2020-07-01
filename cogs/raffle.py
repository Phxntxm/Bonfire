from discord.ext import commands
from collections import defaultdict

import utils

import discord
import re
import asyncio
import random


class Raffle(commands.Cog):
    """Used to hold custom raffles"""
    raffles = defaultdict(list)

    def create_raffle(self, ctx, title, num):
        raffle = GuildRaffle(ctx, title, num)
        self.raffles[ctx.guild.id].append(raffle)
        raffle.start()

    @commands.command(name="raffles")
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def _raffles(self, ctx):
        """Used to print the current running raffles on the server

        EXAMPLE: !raffles
        RESULT: A list of the raffles setup on this server"""
        raffles = self.raffles[ctx.guild.id]
        if len(raffles) == 0:
            await ctx.send("There are currently no raffles setup on this server!")
            return

        embed = discord.Embed(title=f"Raffles in {ctx.guild.name}")

        for num, raffle in enumerate(raffles):
            embed.add_field(
                name=f"Raffle {num + 1}",
                value=f"Title: {raffle.title}\n"
                      f"Total Entrants: {len(raffle.entrants)}\n"
                      f"Ends in {raffle.remaining}",
                inline=False
            )
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def raffle(self, ctx, raffle_id: int):
        """Used to enter a raffle running on this server
        If there is more than one raffle running, provide an ID of the raffle you want to enter

        EXAMPLE: !raffle 1
        RESULT: You've entered the first raffle!"""
        try:
            raffle = self.raffles[ctx.guild.id][raffle_id - 1]
        except IndexError:
            await ctx.send(f"I could not find a raffle for ID {raffle_id}")
            await self._raffles.invoke(ctx)
        else:
            if raffle.enter(ctx.author):
                await ctx.send(f"You have just joined the raffle {raffle['title']}")
            else:
                await ctx.send("You have already entered this raffle!")

    @raffle.command(name='create', aliases=['start', 'begin', 'add'])
    @commands.guild_only()
    @utils.can_run(kick_members=True)
    async def raffle_create(self, ctx):
        """This is used in order to create a new server raffle

        EXAMPLE: !raffle create
        RESULT: A follow-along for setting up a new raffle"""

        author = ctx.author
        channel = ctx.channel

        await ctx.send(
            "Ready to start a new raffle! Please respond with the title you would like to use for this raffle!")

        check = lambda m: m.author == author and m.channel == channel
        try:
            msg = await ctx.bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
            await ctx.send("You took too long! >:c")
            return

        title = msg.content

        fmt = "Alright, your new raffle will be titled:\n\n{}\n\nHow long would you like this raffle to run for? " \
              "The format should be [number] [length] for example, `2 days` or `1 hour` or `30 minutes` etc. " \
              "The minimum for this is 10 minutes, and the maximum is 3 days"
        await ctx.send(fmt.format(title))

        # Our check to ensure that a proper length of time was passed
        def check(m):
            if m.author == author and m.channel == channel:
                return re.search("\d+ (minutes?|hours?|days?)", m.content.lower()) is not None
            else:
                return False

        try:
            msg = await ctx.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long! >:c")
            return

        # Lets get the length provided, based on the number and type passed
        num, term = re.search("(\d+) (minutes?|hours?|days?)", msg.content.lower()).groups()
        # This should be safe to convert, we already made sure with our check earlier this would match
        num = int(num)

        # Now lets ensure this meets our min/max
        if "minute" in term:
            num = num * 60
        elif "hour" in term:
            num = num * 60 * 60
        elif "day" in term:
            num = num * 24 * 60 * 60

        if not 60 < num < 259200:
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 days")
            return

        self.create_raffle(ctx, title, num)
        await ctx.send("I have just saved your new raffle!")


def setup(bot):
    bot.add_cog(Raffle(bot))


class GuildRaffle:

    def __init__(self, ctx, title, expires):
        self._ctx = ctx
        self.title = title
        self.expires = expires
        self.entrants = set()
        self.task = None

    @property
    def guild(self):
        return self._ctx.guild

    @property
    def db(self):
        return self._ctx.bot.db

    def start(self):
        self.task = self._ctx.bot.loop.call_later(self.expires, self.end_raffle())

    @property
    def remaining(self):
        minutes, seconds = divmod(self.task.when(), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

    def enter(self, entrant):
        self.entrants.add(entrant)

    async def end_raffle(self):
        entrants = {e for e in self.entrants if self.guild.get_member(e.id)}

        query = """
SELECT
    COALESCE(raffle_alerts, default_alerts) AS channel,
FROM
    guilds
WHERE
    id = $1
AND
    COALESCE(raffle_alerts, default_alerts) IS NOT NULL
        """
        channel = None
        result = await self.db.fetch(query, self.guild.id)

        if result:
            channel = self.guild.get_channel(result['channel'])
        if channel is None:
            return

        if entrants:
            winner = random.SystemRandom().choice(self.entrants)
            await channel.send(f"The winner of the raffle `{self.title}` is {winner.mention}! Congratulations!")
        else:
            await channel.send(
                f"There were no entrants to the raffle `{self.title}`, who are in this server currently!"
            )
