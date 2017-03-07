from discord.ext import commands
import discord

from . import utils

import random
import pendulum
import re
import asyncio
import traceback


class Raffle:
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.raffle_task())

    async def raffle_task(self):
        while True:
            try:
                await self.check_raffles()
            except Exception as error:
                with open("error_log", 'a') as f:
                    traceback.print_tb(error.__traceback__, file=f)
                    print('{0.__class__.__name__}: {0}'.format(error), file=f)
            await asyncio.sleep(900)

    async def check_raffles(self):
        # This is used to periodically check the current raffles, and see if they have ended yet
        # If the raffle has ended, we'll pick a winner from the entrants
        raffles = await utils.get_content('raffles')

        if raffles is None:
            return

        for raffle in raffles:
            server = self.bot.get_guild(raffle['server_id'])

            # Check to see if this cog can find the server in question
            if server is None:
                continue

            now = pendulum.utcnow()
            expires = pendulum.parse(raffle['expires'])

            # Now lets compare and see if this raffle has ended, if not just continue
            if expires > now:
                continue

            title = raffle['title']
            entrants = raffle['entrants']
            raffle_id = raffle['id']

            # Make sure there are actually entrants
            if len(entrants) == 0:
                fmt = 'Sorry, but there were no entrants for the raffle `{}`!'.format(title)
            else:
                winner = None
                count = 0
                while winner is None:
                    winner = server.get_member(random.SystemRandom().choice(entrants))

                    # Lets make sure we don't get caught in an infinite loop
                    # Realistically having more than 25 random entrants found that aren't in the server anymore
                    # Isn't something that should be an issue
                    count += 1
                    if count >= 25:
                        break

                if winner is None:
                    fmt = 'I couldn\'t find an entrant that is still in this server, for the raffle `{}`!'.format(title)
                else:
                    fmt = 'The raffle `{}` has just ended! The winner is {}!'.format(title, winner.display_name)

            # No matter which one of these matches were met, the raffle has ended and we want to remove it
            # We don't have to wait for it however, so create a task for it
            r_filter = {'id': raffle_id}
            self.bot.loop.create_task(utils.remove_content('raffles', r_filter))
            try:
                await server.send(fmt)
            except discord.Forbidden:
                pass

    @commands.command(no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def raffles(self, ctx):
        """Used to print the current running raffles on the server

        EXAMPLE: !raffles
        RESULT: A list of the raffles setup on this server"""
        r_filter = {'server_id': ctx.message.guild.id}
        raffles = await utils.get_content('raffles', r_filter)
        if raffles is None:
            await ctx.send("There are currently no raffles setup on this server!")
            return

        fmt = "\n\n".join("**Raffle:** {}\n**Title:** {}\n**Total Entrants:** {}\n**Ends:** {} UTC".format(
            num + 1,
            raffle['title'],
            len(raffle['entrants']),
            raffle['expires']) for num, raffle in enumerate(raffles))
        await ctx.send(fmt)

    @commands.group(no_pm=True, invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def raffle(self, ctx, raffle_id: int = 0):
        """Used to enter a raffle running on this server
        If there is more than one raffle running, provide an ID of the raffle you want to enter

        EXAMPLE: !raffle 1
        RESULT: You've entered the first raffle!"""
        # Lets let people use 1 - (length of raffles) and handle 0 base ourselves
        raffle_id -= 1
        r_filter = {'server_id': ctx.message.guild.id}
        author = ctx.message.author

        raffles = await utils.get_content('raffles', r_filter)
        if raffles is None:
            await ctx.send("There are currently no raffles setup on this server!")
            return

        raffle_count = len(raffles)

        # There is only one raffle, so use the first's info
        if raffle_count == 1:
            entrants = raffles[0]['entrants']
            # Lets make sure that the user hasn't already entered the raffle
            if author.id in entrants:
                await ctx.send("You have already entered this raffle!")
                return
            entrants.append(author.id)

            # Since we have no good thing to filter things off of, lets use the internal rethinkdb id
            r_filter = {'id': raffles[0]['id']}
            update = {'entrants': entrants}
            await utils.update_content('raffles', update, r_filter)
            await ctx.send("{} you have just entered the raffle!".format(author.mention))
        # Otherwise, make sure the author gave a valid raffle_id
        elif raffle_id in range(raffle_count - 1):
            entrants = raffles[raffle_id]['entrants']

            # Lets make sure that the user hasn't already entered the raffle
            if author.id in entrants:
                await ctx.send("You have already entered this raffle!")
                return
            entrants.append(author.id)

            # Since we have no good thing to filter things off of, lets use the internal rethinkdb id
            r_filter = {'id': raffles[raffle_id]['id']}
            update = {'entrants': entrants}
            await utils.update_content('raffles', update, r_filter)
            await ctx.send("{} you have just entered the raffle!".format(author.mention))
        else:
            fmt = "Please provide a valid raffle ID, as there are more than one setup on the server! " \
                  "There are currently `{}` raffles running, use {}raffles to view the current running raffles".format(
                      raffle_count, ctx.prefix)
            await ctx.send(fmt)

    @raffle.command(pass_context=True, no_pm=True, name='create', aliases=['start', 'begin', 'add'])
    @utils.custom_perms(kick_members=True)
    async def raffle_create(self, ctx):
        """This is used in order to create a new server raffle

        EXAMPLE: !raffle create
        RESULT: A follow-along for setting up a new raffle"""

        author = ctx.message.author
        server = ctx.message.guild
        channel = ctx.message.channel
        now = pendulum.utcnow()

        await ctx.send(
            "Ready to start a new raffle! Please respond with the title you would like to use for this raffle!")

        check = lambda m: m.author == author and m.channel == channel
        msg = await self.bot.wait_for('message', check=check, timeout=120)

        if msg is None:
            await ctx.send("You took too long! >:c")
            return

        title = msg.content

        fmt = "Alright, your new raffle will be titled:\n\n{}\n\nHow long would you like this raffle to run for? " \
              "The format should be [number] [length] for example, `2 days` or `1 hour` or `30 minutes` etc. " \
              "The minimum for this is 10 minutes, and the maximum is 3 months"
        await ctx.send(fmt.format(title))

        # Our check to ensure that a proper length of time was passed
        def check(m):
            if m.author == author and m.channel == channel:
                return re.search("\d+ (minutes?|hours?|days?|weeks?|months?)", m.content.lower()) is not None
            else:
                return False
        msg = await self.bot.wait_for('message', timeout=120, check=check)

        if msg is None:
            await ctx.send("You took too long! >:c")
            return

        # Lets get the length provided, based on the number and type passed
        num, term = re.search("\d+ (minutes?|hours?|days?|weeks?|months?)", msg.content.lower()).group(0).split(' ')
        # This should be safe to convert, we already made sure with our check earlier this would match
        num = int(num)

        # Now lets ensure this meets our min/max
        if "minute" in term and (num < 10 or num > 129600):
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "hour" in term and num > 2160:
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "day" in term and num > 90:
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "week" in term and num > 12:
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "month" in term and num > 3:
            await ctx.send(
                "Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return

        # Pendulum only accepts the plural version of terms, lets make sure this is added
        term = term if term.endswith('s') else term + 's'
        # If we're in the range, lets just pack this in a dictionary we can pass to set the time we want, then set that
        payload = {term: num}
        expires = now.add(**payload)

        # Now we're ready to add this as a new raffle
        entry = {'title': title,
                 'expires': expires.to_datetime_string(),
                 'entrants': [],
                 'author': author.id,
                 'server_id': server.id}

        # We don't want to pass a filter to this, because we can have multiple raffles per server
        await utils.add_content('raffles', entry)
        await ctx.send("I have just saved your new raffle!")


def setup(bot):
    bot.add_cog(Raffle(bot))
