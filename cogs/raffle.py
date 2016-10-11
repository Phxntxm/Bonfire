from discord.ext import commands
from .utils import config
from .utils import checks

import discord
import pendulum
import re

class Raffle:
    def __init__(self, bot):
        self.bot = bot

    async def check_raffles(self):
        # This is used to periodically check the current raffles, and see if they have ended yet
        # If the raffle has ended, we'll pick a winner from the entrants
        pass

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def raffles(self, ctx):
        """Used to print the current running raffles on the server"""
        r_filter = {'server_id': ctx.message.server.id}
        raffles = await config.get_content('raffles', r_filter)
        if raffles is None:
            await self.bot.say("There are currently no raffles setup on this server!")
            return

        fmt = "\n\n".join("**Raffle:** {}\n**Title:** {}\n**Total Entrants:** {}\n**Ends:** {}".format(
                                                                                       num,
                                                                                       raffle['title'],
                                                                                       len(raffle['entrants']),
                                                                                       raffle['expires']) for num, raffle in enumerate(raffles))


    @commands.group(pass_context=True, no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def raffle(self, ctx, raffle_id: int = 0):
        """Used to enter a raffle running on this server
        If there is more than one raffle running, provide an ID of the raffle you want to enter"""
        # Lets let people use 1 - (length of raffles) and handle 0 base ourselves
        raffle_id -= 1
        r_filter = {'server_id': ctx.message.server.id}
        author = ctx.message.author

        raffles = await config.get_content('raffles', r_filter)
        if raffles is None:
            await self.bot.say("There are currently no raffles setup on this server!")
            return

        raffle_count = len(raffles)

        # There is only one raffle, so use the first's info
        if raffle_count == 1:
            entrants = raffles[0]['entrants']
            # Lets make sure that the user hasn't already entered the raffle
            if author.id in entrants:
                await self.bot.say("You have already entered this raffle!")
                return
            entrants.append(author.id)

            # Since we have no good thing to filter things off of, lets use the internal rethinkdb id
            r_filter = {'id': raffles[0]['id']}
            update = {'entrants': entrants}
            await self.bot.update_content('raffles', update, r_filter)
            await self.bot.say("{} you have just entered the raffle!".format(author.mention))
        # Otherwise, make sure the author gave a valid raffle_id
        elif raffle_id in range(raffle_count):
            entrants = raffles[raffle_id]['entrants']

            # Lets make sure that the user hasn't already entered the raffle
            if author.id in entrants:
                await self.bot.say("You have already entered this raffle!")
                return
            entrants.append(author.id)

            # Since we have no good thing to filter things off of, lets use the internal rethinkdb id
            r_filter = {'id': raffles[1]['id']}
            update = {'entrants': entrants}
            await self.bot.update_content('raffles', update, r_filter)
            await self.bot.say("{} you have just entered the raffle!".format(author.mention))
        else:
            fmt = "Please provide a valid raffle ID, as there are more than one setup on the server! "\
                       "There are currently `{}` raffles running, use {}raffles to view the current running raffles".format(
                                    raffle_count, ctx.prefix)
            await self.bot.say(fmt)

    @raffle.command(pass_context=True, no_pm=True, name='create', aliases=['start', 'begin', 'add'])
    @checks.custom_perms(kick_members=True)
    async def raffle_create(self, ctx):
        """This is used in order to create a new server raffle"""

        author = ctx.message.author
        server = ctx.message.server
        channel = ctx.message.channel
        now = pendulum.utcnow()

        await self.bot.say("Ready to start a new raffle! Please respond with the title you would like to use for this raffle!")

        msg = await self.bot.wait_for_message(author=author, channel=channel, timeout=120)
        if msg is None:
            await self.bot.say("You took too long! >:c")
            return

        title = msg.content

        fmt = "Alright, your new raffle will be titled:\n\n{}\n\nHow long would you like this raffle to run for? " \
                   "The format should be [number] [length] for example, `2 days` or `1 hour` or `30 minutes` etc. "\
                   "The minimum for this is 10 minutes, and the maximum is 3 months"
        await self.bot.say(fmt.format(title))

        # Our check to ensure that a proper length of time was passed
        check = lambda m: re.search("\d+ (minutes?|hours?|days?|weeks?|months?)", m.content.lower()) is not None
        msg = await self.bot.wait_for_message(author=author, channel=channel, timeout=120, check=check)
        if msg is None:
            await self.bot.say("You took too long! >:c")
            return

        # Lets get the length provided, based on the number and type passed
        num, term = re.search("\d+ (minutes?|hours?|days?|weeks?|months?)", msg.content.lower()).group(0).split(' ')
        # This should be safe to convert, we already made sure with our check earlier this would match
        num = int(num)

        # Now lets ensure this meets our min/max
        if "minute" in term and (num < 15 or num > 129600):
            await self.bot.say("Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "hour" in term and num > 2160:
            await self.bot.say("Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "day" in term and num > 90:
            await self.bot.say("Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "week" in term and num > 12:
            await self.bot.say("Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return
        elif "month" in term and num > 3:
            await self.bot.say("Length provided out of range! The minimum for this is 10 minutes, and the maximum is 3 months")
            return

        # Pendulum only accepts the plural version of terms, lets make sure this is added
        term = term if term.endswith('s') else '{}s'.format(term)
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
        await config.add_content('raffles', entry)
        await self.bot.say("I have just created ")

def setup(bot):
    bot.add_cog(Raffle(bot))
