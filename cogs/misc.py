import discord
from discord.ext import commands

from . import utils

from bs4 import BeautifulSoup as bs
import subprocess
import glob
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
    async def help(self, ctx, *, message=None):
        """This command is used to provide a link to the help URL.
        This can be called on a command to provide more information about that command
        You can also provide a page number to pull up that page instead of the first page

        EXAMPLE: !help help
        RESULT: This information"""
        groups = {}
        entries = []

        for cmd in utils.get_all_commands(self.bot):
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
                entry['fields'].append({
                    'name': "**{}**".format(cmd.qualified_name),
                    'value': description,
                    'inline': False
                })
            entries.append(entry)

        try:
            pages = utils.DetailedPages(self.bot, message=ctx.message, entries=entries)
            pages.embed.set_thumbnail(url=self.bot.user.avatar_url)
            await pages.paginate()
        except utils.CannotPaginate as e:
            await ctx.send(str(e))


    @commands.command()
    @utils.custom_perms(send_messages=True)
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
    async def motd(self, ctx, *, date=None):
        """This command can be used to print the current MOTD (Message of the day)
        This will most likely not be updated every day, however messages will still be pushed to this every now and then

        EXAMPLE: !motd
        RESULT: 'This is an example message of the day!'"""
        if date is None:
            motd = await utils.get_content('motd')
            try:
                # Lets set this to the first one in the list first
                latest_motd = motd[0]
                for entry in motd:
                    d = pendulum.parse(entry['date'])

                    # Check if the date for this entry is newer than our currently saved latest entry
                    if d > pendulum.parse(latest_motd['date']):
                        latest_motd = entry

                date = latest_motd['date']
                motd = latest_motd['motd']
            # This will be hit if we do not have any entries for motd
            except TypeError:
                await ctx.send("No message of the day!")
            else:
                fmt = "Last updated: {}\n\n{}".format(date, motd)
                await ctx.send(fmt)
        else:
            try:
                motd = await utils.get_content('motd', str(pendulum.parse(date).date()))
                date = motd['date']
                motd = motd['motd']
                fmt = "Message of the day for {}:\n\n{}".format(date, motd)
                await ctx.send(fmt)
            # This one will be hit if we return None for that day
            except TypeError:
                await ctx.send("No message of the day for {}!".format(date))
            # This will be hit if pendulum fails to parse the date passed
            except ValueError:
                now = pendulum.utcnow().to_date_string()
                await ctx.send("Invalid date format! Try like {}".format(now))

    @commands.command()
    @utils.custom_perms(send_messages=True)
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
    async def info(self, ctx):
        """This command can be used to print out some of my information"""
        # fmt is a dictionary so we can set the key to it's output, then print both
        # The only real use of doing it this way is easier editing if the info
        # in this command is changed

        # Create the original embed object
        opts = {'title': 'Dev Server',
                'description': 'Join the server above for any questions/suggestions about me.',
                'url': utils.dev_server}
        embed = discord.Embed(**opts)

        # Add the normal values
        embed.add_field(name='Total Servers', value=len(self.bot.guilds))
        embed.add_field(name='Total Members', value=len(self.bot.users))

        # Count the variable values; hangman, tictactoe, etc.
        hm_games = len(self.bot.get_cog('Hangman').games)

        ttt_games = len(self.bot.get_cog('TicTacToe').boards)

        bj_games = len(self.bot.get_cog('Blackjack').games)

        count_battles = 0
        for battles in self.bot.get_cog('Interaction').battles.values():
            count_battles += len(battles)

        if hm_games:
            embed.add_field(name='Total Hangman games running', value=hm_games)
        if ttt_games:
            embed.add_field(name='Total TicTacToe games running', value=ttt_games)
        if count_battles:
            embed.add_field(name='Total battles games running', value=count_battles)
        if bj_games:
            embed.add_field(name='Total blackjack games running', value=bj_games)

        if hasattr(self.bot, 'uptime'):
            embed.add_field(name='Uptime', value=(pendulum.utcnow() - self.bot.uptime).in_words())

        memory_usage = self.process.memory_full_info().uss / 1024**2
        cpu_usage = self.process.cpu_percent() / psutil.cpu_count()
        embed.add_field(name='Memory Usage', value='{:.2f} MiB'.format(memory_usage))
        embed.add_field(name='CPU Usage', value='{}%'.format(cpu_usage))
        embed.set_footer(text=self.bot.description)

        await ctx.send(embed=embed)

    @commands.command()
    @utils.custom_perms(send_messages=True)
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
        await ctx.send("Use this URL to add me to a server that you'd like!\n{}"
                       .format(discord.utils.oauth_url(app_info.id, perms)))

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def joke(self, ctx):
        """Prints a random riddle

        EXAMPLE: !joke
        RESULT: An absolutely terrible joke."""
        # Use the fortune riddles command because it's funny, I promise
        fortune_command = "/usr/bin/fortune riddles"
        while True:
            try:
                fortune = subprocess.check_output(
                    fortune_command.split()).decode("utf-8")
                await ctx.send(fortune)
            except discord.HTTPException:
                pass
            else:
                break

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def roll(self, ctx, notation: str = "d6"):
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
        if dice > 10:
            await ctx.send("I'm not rolling more than 10 dice, I have tiny hands")
            return
        if num > 100:
            await ctx.send("What die has more than 100 sides? Please, calm down")
            return
        if num <= 1:
            await ctx.send("A {} sided die? You know that's impossible right?".format(num))
            return

        nums = [random.SystemRandom().randint(1, num) for _ in range(0, int(dice))]
        total = sum(nums)
        value_str = ", ".join("{}".format(x) for x in nums)

        if dice == 1:
            fmt = '{0.message.author.name} has rolled a {2} sided die and got the number {3}!'
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}, for a total of {4}!'
        await ctx.send(fmt.format(ctx, dice, num, value_str, total))


def setup(bot):
    bot.add_cog(Miscallaneous(bot))