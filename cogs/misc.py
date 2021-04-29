import discord
from discord.ext import commands

import utils

import random
import re
import calendar
import inspect
import io
import pendulum
import datetime
import psutil


def _command_signature(cmd):
    result = [cmd.qualified_name]
    if cmd.usage:
        result.append(cmd.usage)
        return " ".join(result)

    params = cmd.clean_params
    if not params:
        return " ".join(result)

    for name, param in params.items():
        if param.default is not param.empty:
            # We don't want None or '' to trigger the [name=value] case and instead it should
            # do [name] since [name=None] or [name=] are not exactly useful for the user.
            should_print = (
                param.default
                if isinstance(param.default, str)
                else param.default is not None
            )
            if should_print:
                result.append(f"[{name}={param.default!r}]")
            else:
                result.append(f"[{name}]")
        elif param.kind == param.VAR_POSITIONAL:
            result.append(f"[{name}...]")
        else:
            result.append(f"<{name}>")

    return " ".join(result)


class Miscellaneous(commands.Cog):
    """Core commands, these are the miscallaneous commands that don't fit into other categories'"""

    process = psutil.Process()
    process.cpu_percent()

    @commands.command()
    @commands.cooldown(1, 3, commands.cooldowns.BucketType.user)
    @utils.can_run(send_messages=True)
    async def help(self, ctx, *, command: str = None):
        """Shows help about a command or the bot"""
        try:
            if command is None:
                p = await utils.HelpPaginator.from_bot(ctx)
            else:
                entity = ctx.bot.get_cog(command) or ctx.bot.get_command(command)

                if entity is None:
                    clean = command.replace("@", "@\u200b")
                    return await ctx.send(f'Command or category "{clean}" not found.')
                elif isinstance(entity, commands.Command):
                    p = await utils.HelpPaginator.from_command(ctx, entity)
                else:
                    p = await utils.HelpPaginator.from_cog(ctx, entity)

            await p.paginate()
        except utils.CannotPaginate:
            await ctx.send(
                "I need embed links permissions in order to do this command :("
            )

    @commands.command()
    @utils.can_run(send_messages=True)
    async def ping(self, ctx):
        """Returns the latency between the server websocket, and between reading messages"""
        msg_latency = datetime.datetime.utcnow() - ctx.message.created_at
        fmt = "Message latency {0:.2f} seconds".format(
            msg_latency.seconds + msg_latency.microseconds / 1000000
        )
        fmt += "\nWebsocket latency {0:.2f} seconds".format(ctx.bot.latency)
        await ctx.send(fmt)

    @commands.command(aliases=["coin"])
    @utils.can_run(send_messages=True)
    async def coinflip(self, ctx):
        """Flips a coin and responds with either heads or tails

        EXAMPLE: !coinflip
        RESULT: Heads!"""

        result = "Heads!" if random.SystemRandom().randint(0, 1) else "Tails!"
        await ctx.send(result)

    @commands.command()
    @utils.can_run(send_messages=True)
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say

        EXAMPLE: !say I really like orange juice
        RESULT: I really like orange juice"""
        fmt = "\u200B{}".format(msg)
        await ctx.send(fmt)
        try:
            await ctx.message.delete()
        except Exception:
            pass

    @commands.command()
    @utils.can_run(send_messages=True)
    async def calendar(self, ctx, month: str = None, year: int = None):
        """Provides a printout of the current month's calendar
        Provide month and year to print the calendar of that year and month

        EXAMPLE: !calendar january 2011"""

        # calendar takes in a number for the month, not the words
        # so we need this dictionary to transform the word to the number
        months = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        # In month was not passed, use the current month
        if month is None:
            month = datetime.date.today().month
        else:
            month = months.get(month.lower())
            if month is None:
                await ctx.send("Please provide a valid Month!")
                return
        # If year was not passed, use the current year
        if year is None:
            year = datetime.datetime.today().year
        # Here we create the actual "text" calendar that we are printing
        cal = calendar.TextCalendar().formatmonth(year, month)
        await ctx.send("```\n{}```".format(cal))

    @commands.command(aliases=["about"])
    @utils.can_run(send_messages=True)
    async def info(self, ctx):
        """This command can be used to print out some of my information"""
        # fmt is a dictionary so we can set the key to it's output, then print both
        # The only real use of doing it this way is easier editing if the info
        # in this command is changed

        # Create the original embed object
        # Set the description include dev server (should be required) and the optional patreon link
        description = "[Dev Server]({})".format(utils.dev_server)
        if utils.patreon_link:
            description += "\n[Patreon]({})".format(utils.patreon_link)
        # Now creat the object
        opts = {
            "title": "Bonfire",
            "description": description,
            "colour": discord.Colour.green(),
        }

        # Set the owner
        embed = discord.Embed(**opts)
        if hasattr(ctx.bot, "owner"):
            embed.set_author(name=str(ctx.bot.owner), icon_url=ctx.bot.owner.avatar_url)

        # Setup the process statistics
        name = "Process statistics"
        value = ""

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent()
        value += "Memory: {:.2f} MiB".format(memory_usage)
        value += "\nCPU: {}%".format(cpu_usage)
        if hasattr(ctx.bot, "uptime"):
            value += "\nUptime: {}".format(
                (pendulum.now(tz="UTC") - ctx.bot.uptime).in_words()
            )
        embed.add_field(name=name, value=value, inline=False)

        # Setup the user and guild statistics
        name = "User/Guild statistics"
        value = ""

        value += "Channels: {}".format(len(list(ctx.bot.get_all_channels())))
        value += "\nUsers: {}".format(len(ctx.bot.users))
        value += "\nServers: {}".format(len(ctx.bot.guilds))
        embed.add_field(name=name, value=value, inline=False)

        # The game statistics
        name = "Game statistics"
        # To get the newlines right, since we're not sure what will and won't be included
        # Lets make this one a list and join it at the end
        value = []

        hm = ctx.bot.get_cog("Hangman")
        ttt = ctx.bot.get_cog("TicTacToe")
        bj = ctx.bot.get_cog("Blackjack")
        interaction = ctx.bot.get_cog("Interaction")

        if hm:
            value.append("Hangman games: {}".format(len(hm.games)))
        if ttt:
            value.append("TicTacToe games: {}".format(len(ttt.boards)))
        if bj:
            value.append("Blackjack games: {}".format(len(bj.games)))
        if interaction:
            count_battles = 0
            for battles in ctx.bot.get_cog("Interaction").battles.values():
                count_battles += len(battles)
            value.append("Battles running: {}".format(len(bj.games)))
        embed.add_field(name=name, value="\n".join(value), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @utils.can_run(send_messages=True)
    async def uptime(self, ctx):
        """Provides a printout of the current bot's uptime

        EXAMPLE: !uptime
        RESULT: A BAJILLION DAYS"""
        if hasattr(ctx.bot, "uptime"):
            await ctx.send(
                "Uptime: ```\n{}```".format(
                    (pendulum.now(tz="UTC") - ctx.bot.uptime).in_words()
                )
            )
        else:
            await ctx.send(
                "I've just restarted and not quite ready yet...gimme time I'm not a morning pony :c"
            )

    @commands.command(aliases=["invite"])
    @utils.can_run(send_messages=True)
    async def addbot(self, ctx):
        """Provides a link that you can use to add me to a server

        EXAMPLE: !addbot
        RESULT: http://discord.gg/yo_mama"""
        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.send_messages = True
        perms.manage_roles = True
        perms.ban_members = True
        perms.kick_members = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        perms.speak = True
        perms.connect = True
        perms.attach_files = True
        perms.add_reactions = True
        app_info = await ctx.bot.application_info()
        await ctx.send(
            "Use this URL to add me to a server that you'd like!\n<{}>".format(
                discord.utils.oauth_url(app_info.id, perms)
            )
        )

    @commands.command()
    @utils.can_run(send_messages=True)
    async def source(self, ctx, *, command: str = None):
        """Displays my full source code or for a specific command.

        EXAMPLE: !source source
        RESULTS: Shows the code for this command!
        """
        source_url = "https://github.com/Phxntxm/Bonfire"
        branch = "master"
        if command is None:
            return await ctx.send(source_url)

        obj = ctx.bot.get_command(command)
        if obj is None:
            return await ctx.send(f"Could not find command {command}")

        # Get source from the callback
        src = obj.callback.__code__
        lines, firstlineno = inspect.getsourcelines(src)
        location = os.path.relpath(src.co_filename).replace("\\", "/")

        final_url = f"<{source_url}/blob/{branch}/{location}#L{firstlineno}-L{firstlineno + len(lines) - 1}>"
        # Provide the source as a file, for the preview file thing
        src = io.StringIO(inspect.getsource(src))
        await ctx.send(final_url, file=discord.File(src, filename=f"{command}.py"))

    @commands.command(enabled=False)
    @utils.can_run(send_messages=True)
    async def joke(self, ctx):
        """Prints a random riddle

        EXAMPLE: !joke
        RESULT: An absolutely terrible joke."""
        # Currently disabled until I can find a free API
        pass

    @commands.command()
    @utils.can_run(send_messages=True)
    async def roll(self, ctx, *, notation: str = "d6"):
        """Rolls a die based on the notation given
        Format should be #d#

        EXAMPLE: !roll d50
        RESULT: 51 :^)"""
        # Use regex to get the notation based on what was provided
        try:
            # We do not want to try to convert the dice, because we want d# to
            # be a valid notation
            dice = re.search(r"(\d*)d(\d*)", notation).group(1)
            num = int(re.search(r"(\d*)d(\d*)", notation).group(2))
            # Attempt to get addition/subtraction
            add = re.search(r"\+ ?(\d+)", notation)
            subtract = re.search(r"- ?(\d+)", notation)
        # Check if something like ed3 was provided, or something else entirely
        # was provided
        except (AttributeError, ValueError):
            await ctx.send("Please provide the die notation in #d#!")
            return

        # Dice will be None if d# was provided, assume this means 1d#
        dice = dice or 1
        # Since we did not try to convert to int before, do it now after we
        # have it set
        dice = int(dice)
        if dice > 30:
            await ctx.send("I'm not rolling more than 30 dice, I have tiny hands")
            return
        if num > 100:
            await ctx.send("What die has more than 100 sides? Please, calm down")
            return
        if num <= 1:
            await ctx.send(
                "A {} sided die? You know that's impossible right?".format(num)
            )
            return

        nums = [random.SystemRandom().randint(1, num) for _ in range(0, int(dice))]
        subtotal = total = sum(nums)
        # After totalling, if we have add/subtract seperately, apply them
        if add:
            add = int(add.group(1))
            total += add
        if subtract:
            subtract = int(subtract.group(1))
            total -= subtract
        value_str = ", ".join("{}".format(x) for x in nums)

        if dice == 1:
            fmt = "{0.message.author.name} has rolled a {1} sided die and got the number {2}!".format(
                ctx, num, value_str
            )
            if add or subtract:
                fmt += "\nTotal: {} ({}".format(total, subtotal)
                if add:
                    fmt += " + {}".format(add)
                if subtract:
                    fmt += " - {}".format(subtract)
                fmt += ")"
        else:
            fmt = "{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!".format(
                ctx, dice, num, value_str
            )
            if add or subtract:
                fmt += "\nTotal: {} ({}".format(total, subtotal)
                if add:
                    fmt += " + {}".format(add)
                if subtract:
                    fmt += " - {}".format(subtract)
                fmt += ")"
            else:
                fmt += "\nTotal: {}".format(total)
        await ctx.send(fmt)


def setup(bot):
    bot.add_cog(Miscellaneous(bot))
