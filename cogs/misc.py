import discord
from discord.ext import commands

from . import utils

import random
import re
import calendar
import pendulum
import datetime
import psutil


class Miscallaneous:
    """Core commands, these are the miscallaneous commands that don't fit into other categories'"""

    def __init__(self, bot):
        self.bot = bot
        self.help_embeds = []
        self.results_per_page = 10
        self.commands = None
        self.process = psutil.Process()
        self.process.cpu_percent()

    @commands.command()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def help(self, ctx, *, command=None):
        """This command is used to provide a link to the help URL.
        This can be called on a command to provide more information about that command
        You can also provide a page number to pull up that page instead of the first page

        EXAMPLE: !help help
        RESULT: This information"""
        groups = {}
        entries = []

        if command is not None:
            command = self.bot.get_command(command)

        if command is None:
            for cmd in utils.get_all_commands(self.bot):
                try:
                    if not await cmd.can_run(ctx) or not cmd.enabled:
                        continue
                except commands.errors.MissingPermissions:
                    continue

                cog = cmd.cog_name
                if cog in groups:
                    groups[cog].append(cmd)
                else:
                    groups[cog] = [cmd]

            for cog, cmds in groups.items():
                entry = {'title': "{} Commands".format(cog),
                         'fields': []}

                for cmd in cmds:
                    if not cmd.help:
                        # Assume if there's no description for a command, it's not supposed to be used
                        # I.e. the !command command. It's just a parent
                        continue

                    description = cmd.help.partition('\n')[0]
                    name_fmt = "{ctx.prefix}**{cmd.qualified_name}** {aliases}".format(
                        ctx=ctx,
                        cmd=cmd,
                        aliases=cmd.aliases if len(cmd.aliases) > 0 else ""
                    )
                    entry['fields'].append({
                        'name': name_fmt,
                        'value': description,
                        'inline': False
                    })
                entries.append(entry)

            entries = sorted(entries, key=lambda x: x['title'])
            try:
                pages = utils.DetailedPages(self.bot, message=ctx.message, entries=entries)
                pages.embed.set_thumbnail(url=self.bot.user.avatar_url)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))
        else:
            # Get the description for a command
            description = command.help
            if description is not None:
                # Split into examples, results, and the description itself based on the string
                description, _, rest = command.help.partition('EXAMPLE:')
                example, _, result = rest.partition('RESULT:')
            else:
                example = None
                result = None
            # Also get the subcommands for this command, if they exist
            subcommands = [x.qualified_name for x in utils.get_all_subcommands(command) if x != command]

            # The rest is simple, create the embed, set the thumbail to me, add all fields if they exist
            embed = discord.Embed(title=command.qualified_name)
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            if description:
                embed.add_field(name="Description", value=description.strip(), inline=False)
            if example:
                embed.add_field(name="Example", value=example.strip(), inline=False)
            if result:
                embed.add_field(name="Result", value=result.strip(), inline=False)
            if subcommands:
                embed.add_field(name='Subcommands', value="\n".join(subcommands), inline=False)

            await ctx.send(embed=embed)

    @commands.command()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def say(self, ctx, *, msg: str):
        """Tells the bot to repeat what you say

        EXAMPLE: !say I really like orange juice
        RESULT: I really like orange juice"""
        fmt = "\u200B{}".format(msg)
        await ctx.send(fmt)
        try:
            await ctx.message.delete()
        except:
            pass

    @commands.command()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
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
            "december": 12
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

    @commands.command(aliases=['about'])
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
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
        opts = {'title': 'Bonfire',
                'description': description,
                'colour': discord.Colour.green()}

        # Set the owner
        embed = discord.Embed(**opts)
        if hasattr(self.bot, 'owner'):
            embed.set_author(name=str(self.bot.owner), icon_url=self.bot.owner.avatar_url)

        # Setup the process statistics
        name = "Process statistics"
        value = ""

        memory_usage = self.process.memory_full_info().uss / 1024 ** 2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        value += 'Memory: {:.2f} MiB'.format(memory_usage)
        value += '\nCPU: {}%'.format(cpu_usage)
        if hasattr(self.bot, 'uptime'):
            value += "\nUptime: {}".format((pendulum.utcnow() - self.bot.uptime).in_words())
        embed.add_field(name=name, value=value, inline=False)

        # Setup the user and guild statistics
        name = "User/Guild statistics"
        value = ""

        value += "Channels: {}".format(len(list(self.bot.get_all_channels())))
        value += "\nUsers: {}".format(len(self.bot.users))
        value += "\nServers: {}".format(len(self.bot.guilds))
        embed.add_field(name=name, value=value, inline=False)

        # The game statistics
        name = "Game statistics"
        # To get the newlines right, since we're not sure what will and won't be included
        # Lets make this one a list and join it at the end
        value = []

        hm = self.bot.get_cog('Hangman')
        ttt = self.bot.get_cog('TicTacToe')
        bj = self.bot.get_cog('Blackjack')
        interaction = self.bot.get_cog('Interaction')
        music = self.bot.get_cog('Music')

        if hm:
            value.append("Hangman games: {}".format(len(hm.games)))
        if ttt:
            value.append("TicTacToe games: {}".format(len(ttt.boards)))
        if bj:
            value.append("Blackjack games: {}".format(len(bj.games)))
        if interaction:
            count_battles = 0
            for battles in self.bot.get_cog('Interaction').battles.values():
                count_battles += len(battles)
            value.append("Battles running: {}".format(len(bj.games)))
        if music:
            songs = len([x for x in music.voice_states.values() if x.playing])
            value.append("Total songs playing: {}".format(songs))
        embed.add_field(name=name, value="\n".join(value), inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def uptime(self, ctx):
        """Provides a printout of the current bot's uptime

        EXAMPLE: !uptime
        RESULT: A BAJILLION DAYS"""
        if hasattr(self.bot, 'uptime'):
            await ctx.send("Uptime: ```\n{}```".format((pendulum.utcnow() - self.bot.uptime).in_words()))
        else:
            await ctx.send("I've just restarted and not quite ready yet...gimme time I'm not a morning pony :c")

    @commands.command(aliases=['invite'])
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
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
        app_info = await self.bot.application_info()
        await ctx.send("Use this URL to add me to a server that you'd like!\n<{}>"
                       .format(discord.utils.oauth_url(app_info.id, perms)))

    @commands.command(enabled=False)
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def joke(self, ctx):
        """Prints a random riddle

        EXAMPLE: !joke
        RESULT: An absolutely terrible joke."""
        # Currently disabled until I can find a free API
        pass

    @commands.command()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def roll(self, ctx, *, notation: str = "d6"):
        """Rolls a die based on the notation given
        Format should be #d#

        EXAMPLE: !roll d50
        RESULT: 51 :^)"""
        # Use regex to get the notation based on what was provided
        try:
            # We do not want to try to convert the dice, because we want d# to
            # be a valid notation
            dice = re.search("(\d*)d(\d*)", notation).group(1)
            num = int(re.search("(\d*)d(\d*)", notation).group(2))
            # Attempt to get addition/subtraction
            add = re.search("\+ ?(\d+)", notation)
            subtract = re.search("- ?(\d+)", notation)
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
            await ctx.send("A {} sided die? You know that's impossible right?".format(num))
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
            fmt = '{0.message.author.name} has rolled a {1} sided die and got the number {2}!'.format(ctx, num, value_str)
            if add or subtract:
                fmt += "\nTotal: {} ({}".format(total, subtotal)
                if add:
                    fmt += " + {}".format(add)
                if subtract:
                    fmt += " - {}".format(subtract)
                fmt += ")"
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!'.format(ctx, dice, num, value_str)
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
    bot.add_cog(Miscallaneous(bot))
