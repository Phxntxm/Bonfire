import discord
from discord.ext import commands
from .utils import checks
from .utils import config

import subprocess
import glob
import random
import re
import calendar
import pendulum
import datetime


class Core:
    """Core commands, these are the miscallaneous commands that don't fit into other categories'"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def motd(self, *, date=None):
        """This command can be used to print the current MOTD (Message of the day)
        This will most likely not be updated every day, however messages will still be pushed to this every now and then"""
        if date is None:
            motd = await config.get_content('motd')
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
                await self.bot.say("No message of the day!")
            else:
                fmt = "Last updated: {}\n\n{}".format(date, motd)
                await self.bot.say(fmt)
        else:
            try:
                r_filter = pendulum.parse(date)
                motd = await config.get_content('motd', r_filter)
                date = motd[0]['date']
                motd = motd[0]['motd']
                fmt = "Message of the day for {}:\n\n{}".format(date, motd)
                await self.bot.say(fmt)
            # This one will be hit if we return None for that day
            except TypeError:
                await self.bot.say("No message of the day for {}!".format(date))
            # This will be hit if pendulum fails to parse the date passed
            except ValueError:
                now = pendulum.utcnow().to_date_string()
                await self.bot.say("Invalid date format! Try like {}".format(now))

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def calendar(self, month: str = None, year: int = None):
        """Provides a printout of the current month's calendar
        Provide month and year to print the calendar of that year and month"""

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
                await self.bot.say("Please provide a valid Month!")
                return
        # If year was not passed, use the current year
        if year is None:
            year = datetime.datetime.today().year
        # Here we create the actual "text" calendar that we are printing
        cal = calendar.TextCalendar().formatmonth(year, month)
        await self.bot.say("```\n{}```".format(cal))

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def info(self):
        """This command can be used to print out some of my information"""
        # fmt is a dictionary so we can set the key to it's output, then print both
        # The only real use of doing it this way is easier editing if the info
        # in this command is changed
        fmt = {}

        bot_data = await config.get_content('bot_data')
        total_data = {'member_count': 0,
                      'server_count': 0}
        for entry in bot_data:
            total_data['member_count'] += entry['member_count']
            total_data['server_count'] += entry['server_count']

        fmt['Official Bot Server'] = config.dev_server
        fmt['Uptime'] = (pendulum.utcnow() - self.bot.uptime).in_words()
        fmt['Total Servers'] = total_data.get('server_count')
        fmt['Total Members'] = total_data.get('member_count')
        fmt['Description'] = self.bot.description

        servers_playing_music = len([server_id for server_id, state in self.bot.get_cog('Music').voice_states.items() if
                                     state.is_playing()])
        hm_games = len(
            [server_id for server_id, game in self.bot.get_cog('Hangman').games.items()])
        ttt_games = len([server_id for server_id,
                         game in self.bot.get_cog('TicTacToe').boards.items()])
        count_battles = 0
        for battles in self.bot.get_cog('Interaction').battles.values():
            count_battles += len(battles)

        information = "\n".join("{}: {}".format(key, result)
                                for key, result in fmt.items())
        information += "\n"
        if servers_playing_music:
            information += "Playing songs in {} different servers\n".format(
                servers_playing_music)
        if hm_games:
            information += "{} different hangman games running\n".format(
                hm_games)
        if ttt_games:
            information += "{} different TicTacToe games running\n".format(
                ttt_games)
        if count_battles:
            information += "{} different battles going on\n".format(
                count_battles)

        await self.bot.say("```\n{}```".format(information))

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def uptime(self):
        """Provides a printout of the current bot's uptime"""
        await self.bot.say("Uptime: ```\n{}```".format((pendulum.utcnow() - self.bot.uptime).in_words()))

    @commands.command(aliases=['invite'])
    @checks.custom_perms(send_messages=True)
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
        app_info = await self.bot.application_info()
        await self.bot.say("Use this URL to add me to a server that you'd like!\n{}"
                           .format(discord.utils.oauth_url(app_info.id, perms)))

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def doggo(self):
        """Use this to print a random doggo image.
        Doggo is love, doggo is life."""
        # Find a random image based on how many we currently have
        f = random.SystemRandom().choice(glob.glob('images/doggo*'))
        with open(f, 'rb') as f:
            await self.bot.upload(f)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def snek(self):
        """Use this to print a random snek image.
        Sneks are o3o"""
        # Find a random image based on how many we currently have
        f = random.SystemRandom().choice(glob.glob('images/snek*'))
        with open(f, 'rb') as f:
            await self.bot.upload(f)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def joke(self):
        """Prints a random riddle"""
        # Use the fortune riddles command because it's funny, I promise
        fortune_command = "/usr/bin/fortune riddles"
        fortune = subprocess.check_output(
            fortune_command.split()).decode("utf-8")
        await self.bot.say(fortune)

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def roll(self, ctx, notation: str = "d6"):
        """Rolls a die based on the notation given
        Format should be #d#"""
        # Use regex to get the notation based on what was provided
        try:
            # We do not want to try to convert the dice, because we want d# to
            # be a valid notation
            dice = re.search("(\d*)d(\d*)", notation).group(1)
            num = int(re.search("(\d*)d(\d*)", notation).group(2))
        # Check if something like ed3 was provided, or something else entirely
        # was provided
        except (AttributeError, ValueError):
            await self.bot.say("Please provide the die notation in #d#!")
            return

        # Dice will be None if d# was provided, assume this means 1d#
        dice = dice or 1
        # Since we did not try to convert to int before, do it now after we
        # have it set
        dice = int(dice)
        if dice > 10:
            await self.bot.say("I'm not rolling more than 10 dice, I have tiny hands")
            return
        if num > 100:
            await self.bot.say("What die has more than 100 sides? Please, calm down")
            return

        value_str = ", ".join(str(random.SystemRandom().randint(1, num))
                              for i in range(0, int(dice)))

        if dice == 1:
            fmt = '{0.message.author.name} has rolled a {2} sided die and got the number {3}!'
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!'
        await self.bot.say(fmt.format(ctx, dice, num, value_str))


def setup(bot):
    bot.add_cog(Core(bot))
