from discord.ext import commands
import discord

from . import utils

import random
import pendulum
import re
import asyncio
import traceback
import rethinkdb as r


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
            await asyncio.sleep(60)

    async def check_raffles(self):
        # This is used to periodically check the current raffles, and see if they have ended yet
        # If the raffle has ended, we'll pick a winner from the entrants
        raffles = self.bot.db.load('raffles')

        if raffles is None:
            return

        for raffle in raffles:
            server = self.bot.get_guild(int(raffle['server_id']))
            title = raffle['title']
            entrants = raffle['entrants']
            raffle_id = raffle['id']

            # Check to see if this cog can find the server in question
            if server is None:
                await self.bot.db.query(r.table('raffles').get(raffle_id).delete())
                continue

            now = pendulum.utcnow()
            expires = pendulum.parse(raffle['expires'])

            # Now lets compare and see if this raffle has ended, if not just continue
            if expires > now:
                continue

            # Make sure there are actually entrants
            if len(entrants) == 0:
                fmt = 'Sorry, but there were no entrants for the raffle `{}`!'.format(title)
            else:
                winner = None
                count = 0
                while winner is None:
                    winner = server.get_member(int(random.SystemRandom().choice(entrants)))

                    # Lets make sure we don't get caught in an infinite loop
                    # Realistically having more than 50 random entrants found that aren't in the server anymore
                    # Isn't something that should be an issue, but better safe than sorry
                    count += 1
                    if count >= 50:
                        break

                if winner is None:
                    fmt = 'I couldn\'t find an entrant that is still in this server, for the raffle `{}`!'.format(title)
                else:
                    fmt = 'The raffle `{}` has just ended! The winner is {}!'.format(title, winner.display_name)

            # Get the notifications settings, get the raffle setting
            notifications = self.bot.db.load('server_settings', key=server.id, pluck='notifications') or {}
            # Set our default to either the one set, or the default channel of the server
            default_channel_id = notifications.get('default') or server.id
            # If it is has been overriden by picarto notifications setting, use this
            channel_id = notifications.get('raffle') or default_channel_id
            channel = self.bot.get_channel(int(channel_id))
            if channel is None:
                channel = server.default_channel
            try:
                await channel.send(fmt)
            except (discord.Forbidden, AttributeError):
                pass

            # No matter which one of these matches were met, the raffle has ended and we want to remove it
            await self.bot.db.query(r.table('raffles').get(raffle_id).delete())
            # Now...this is an ugly idea yes, but due to the way raffles are setup currently (they'll be changed in
            # the future) The cache does not update, and leaves behind this deletion....so we need to manually update
            #  the cache here
            await self.bot.db.cache.get('raffles').refresh()

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def raffles(self, ctx):
        """Used to print the current running raffles on the server

        EXAMPLE: !raffles
        RESULT: A list of the raffles setup on this server"""
        r_filter = {'server_id': str(ctx.message.guild.id)}
        raffles = self.bot.db.load('raffles', table_filter=r_filter)
        if not raffles:
            await ctx.send("There are currently no raffles setup on this server!")
            return

        # For EVERY OTHER COG, when we get one result, it is nice to have it return that exact object
        # This is the only cog where that is different, so just to make this easier lets throw it
        # back in a one-indexed list, for easier parsing
        if isinstance(raffles, dict):
            raffles = [raffles]
        fmt = "\n\n".join("**Raffle:** {}\n**Title:** {}\n**Total Entrants:** {}\n**Ends:** {} UTC".format(
            num + 1,
            raffle['title'],
            len(raffle['entrants']),
            raffle['expires']) for num, raffle in enumerate(raffles))
        await ctx.send(fmt)

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def raffle(self, ctx, raffle_id: int = 0):
        """Used to enter a raffle running on this server
        If there is more than one raffle running, provide an ID of the raffle you want to enter

        EXAMPLE: !raffle 1
        RESULT: You've entered the first raffle!"""
        # Lets let people use 1 - (length of raffles) and handle 0 base ourselves
        raffle_id -= 1
        r_filter = {'server_id': str(ctx.message.guild.id)}
        author = ctx.message.author

        raffles = self.bot.db.load('raffles', table_filter=r_filter)
        if raffles is None:
            await ctx.send("There are currently no raffles setup on this server!")
            return

        if isinstance(raffles, list):
            raffle_count = len(raffles)
        else:
            raffles = [raffles]
            raffle_count = 1

        # There is only one raffle, so use the first's info
        if raffle_count == 1:
            entrants = raffles[0]['entrants']
            # Lets make sure that the user hasn't already entered the raffle
            if str(author.id) in entrants:
                await ctx.send("You have already entered this raffle!")
                return
            entrants.append(str(author.id))

            update = {
                'entrants': entrants,
                'id': raffles[0]['id']
            }
            self.bot.db.save('raffles', update)
            await ctx.send("{} you have just entered the raffle!".format(author.mention))
        # Otherwise, make sure the author gave a valid raffle_id
        elif raffle_id in range(raffle_count):
            entrants = raffles[raffle_id]['entrants']

            # Lets make sure that the user hasn't already entered the raffle
            if str(author.id) in entrants:
                await ctx.send("You have already entered this raffle!")
                return
            entrants.append(str(author.id))

            # Since we have no good thing to filter things off of, lets use the internal rethinkdb id

            update = {
                'entrants': entrants,
                'id': raffles[raffle_id]['id']
            }
            self.bot.db.save('raffles', update)
            await ctx.send("{} you have just entered the raffle!".format(author.mention))
        else:
            fmt = "Please provide a valid raffle ID, as there are more than one setup on the server! " \
                  "There are currently `{}` raffles running, use {}raffles to view the current running raffles".format(
                    raffle_count, ctx.prefix)
            await ctx.send(fmt)

    @raffle.command(pass_context=True, name='create', aliases=['start', 'begin', 'add'])
    @commands.guild_only()
    @utils.custom_perms(kick_members=True)
    @utils.check_restricted()
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
        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120)
        except asyncio.TimeoutError:
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

        try:
            msg = await self.bot.wait_for('message', timeout=120, check=check)
        except asyncio.TimeoutError:
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
        entry = {
            'title': title,
            'expires': expires.to_datetime_string(),
            'entrants': [],
            'author': str(author.id),
            'server_id': str(server.id)
        }

        # We don't want to pass a filter to this, because we can have multiple raffles per server
        self.bot.db.save('raffles', entry)
        await ctx.send("I have just saved your new raffle!")

    @raffle.command(name='alerts')
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def raffle_alerts_channel(self, ctx, channel: discord.TextChannel):
        """Sets the notifications channel for raffle notifications

        EXAMPLE: !raffle alerts #raffle
        RESULT: raffle notifications will go to this channel
        """
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications': {
                'raffle': str(channel.id)
            }
        }
        self.bot.db.save('server_settings', entry)
        await ctx.send("All raffle notifications will now go to {}".format(channel.mention))


def setup(bot):
    bot.add_cog(Raffle(bot))
