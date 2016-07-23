import discord
from discord.ext import commands
from .utils import config
from .utils import checks

import subprocess
import os
import glob
import random
import re
import calendar
import datetime


class Core:
    """Core commands, these are the miscallaneous commands that don't fit into other categories'"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.customPermsOrRole("send_messages")
    async def calendar(self, month: str=None, year: int=None):
        """Provides a printout of the current month's calendar
        Provide month and year to print the calendar of that year and month"""
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
        if month is None:
            month = datetime.date.today().month
        else:
            month = months.get(month.lower())
            if month is None:
                await self.bot.say("Please provide a valid Month!")
                return
        if year is None:
            year = datetime.datetime.today().year
        cal = calendar.TextCalendar().formatmonth(year, month)
        await self.bot.say("```{}```".format(cal))

    @commands.command()
    @checks.customPermsOrRole("send_messages")
    async def addbot(self):
        """Provides a link that you can use to add me to a server"""
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
        await self.bot.say("Use this URL to add me to a server that you'd like!\n{}"
                           .format(discord.utils.oauth_url('183748889814237186', perms)))

    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def doggo(self, ctx):
        """Use this to print a random doggo image.
        Doggo is love, doggo is life."""
        os.chdir('/home/phxntx5/public_html/Bonfire/images')
        f = glob.glob('doggo*')[random.randint(0, len(glob.glob('doggo*')) - 1)]
        with open(f, 'rb') as f:
            await self.bot.send_file(ctx.message.channel, f)

    @commands.command()
    @checks.customPermsOrRole("send_messages")
    async def joke(self):
        """Prints a random riddle"""
        fortuneCommand = "/usr/bin/fortune riddles"
        fortune = subprocess.check_output(fortuneCommand.split()).decode("utf-8")
        await self.bot.say(fortune)


    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def roll(self, ctx, notation: str="d6"):
        """Rolls a die based on the notation given
        Format should be #d#"""
        try:
            dice = int(re.search("(\d*)d(\d*)", notation).group(1))
            num = int(re.search("(\d*)d(\d*)", notation).group(2))
        # This error will be hit if the notation is completely different than #d#
        except AttributeError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        # This error will be hit if there was an issue converting to an int
        # This means the notation was still given wrong
        except ValueError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        # Dice will be None if d# was provided, assume this means 1d#
        dice = dice or '1'
        if dice > 10:
            await self.bot.say("I'm not rolling more than 10 dice, I have tiny hands")
            return
        if num > 100:
            await self.bot.say("What die has more than 100 sides? Please, calm down")
            return

        valueStr = ", ".join(str(random.randint(1, num)) for i in range(0, int(dice)))

        if int(dice) == 1:
            fmt = '{0.message.author.name} has rolled a {2} sided die and got the number {3}!'
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!'
        await self.bot.say(fmt.format(ctx, dice, num, valueStr))


def setup(bot):
    bot.add_cog(Core(bot))
