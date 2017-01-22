import discord
from discord.ext import commands
from .utils import checks
from .utils import config
from .utils import utilities

import subprocess
import glob
import random
import re
import calendar
import pendulum
import datetime
import math


class Core:
    """Core commands, these are the miscallaneous commands that don't fit into other categories'"""

    def __init__(self, bot):
        self.bot = bot
        # This is a dictionary used to hold information about which page a certain help message is on
        self.help_embeds = {}
        self.results_per_page = 10
        self.commands = None

    async def on_reaction_add(self, reaction, user):
        # Make sure that this is a normal user who pressed the button
        # Also make sure that this is even a message we should be paying attention to
        if user.bot or reaction.message.id not in self.help_embeds:
            return

        # If right is clicked
        if '\u27A1' in reaction.emoji:
            embed = self.next_page(reaction.message.id)
        # If left is clicked
        elif '\u2B05' in reaction.emoji:
            embed = self.prev_page(reaction.message.id)
        else:
            return

        await self.bot.edit_message(reaction.message, embed=embed)
        await self.bot.remove_reaction(reaction.message, reaction.emoji, user)

    def determine_commands(self, page):
        """Returns the list of commands to use per page"""

        end_index = self.results_per_page * page
        start_index = end_index - self.results_per_page

        return self.commands[start_index:end_index]

    def prev_page(self, message_id):
        """Goes to the previus page"""
        total_commands = len(self.commands)
        # Increase the page count by one
        page = self.help_embeds.get(message_id) - 1

        total_pages = math.ceil(total_commands / self.results_per_page)

        # If we hit the zeroith page, set to the very last page
        if page <= 0:
            page = total_pages
        # Set the new page
        self.help_embeds[message_id] = page
        # Now create our new embed
        return self.create_help_embed(message_id=message_id)

    def next_page(self, message_id):
        """Goes to the next page for this message"""
        total_commands = len(self.commands)
        # Increase the page count by one
        page = self.help_embeds.get(message_id) + 1

        total_pages = math.ceil(total_commands / self.results_per_page)

        # Make sure we don't reach past what we should; if we do, reset to page 1
        if page > total_pages:
            page = 1

        # Set the new page
        self.help_embeds[message_id] = page
        # Now create our new embed
        return self.create_help_embed(message_id=message_id)

    def create_help_embed(self, message_id=None, page=1):
        # If a message_id is provided, we need to get the new page (this is being sent by next/prev page buttons)
        if message_id is not None:
            page = self.help_embeds.get(message_id)

        # Refresh our command list
        self.commands = sorted(utilities.get_all_commands(self.bot))

        # Calculate the total amount of pages needed
        total_commands = len(self.commands)
        total_pages = math.ceil(total_commands / self.results_per_page)

        # Lets make sure that if a page was provided, it is within our range of pages available
        if page < 1 or page > total_pages:
            page = 1

        # First create the embed object
        opts = {"title": "Command List [{}/{}]".format(page, total_pages),
                "description": "Run help on a specific command for more information on it!"}
        embed = discord.Embed(**opts)

        # Add each field for the commands for this page
        fmt = "\n".join(self.determine_commands(page))
        embed.add_field(name="Commands", value=fmt, inline=False)

        return embed

    def find_command(self, command):
        # This method ensures the command given is valid. We need to loop through commands
        # As self.bot.commands only includes parent commands
        # So we are splitting the command in parts, looping through the commands
        # And getting the subcommand based on the next part
        # If we try to access commands of a command that isn't a group
        # We'll hit an AttributeError, meaning an invalid command was given
        # If we loop through and don't find anything, cmd will still be None
        # And we'll report an invalid was given as well
        cmd = None

        for part in command.split():
            try:
                if cmd is None:
                    cmd = self.bot.commands.get(part)
                else:
                    cmd = cmd.commands.get(part)
            except AttributeError:
                cmd = None
                break

        return cmd

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def help(self, ctx, *, message=None):
        """This command is used to provide a link to the help URL.
        This can be called on a command to provide more information about that command
        You can also provide a page number to pull up that page instead of the first page

        EXAMPLE: !help help
        RESULT: This information"""

        cmd = None
        page = 1
        if message is None:
            message = ""
        else:
            # If something is provided, it can either be the page number or a command
            # Try to convert to an int (the page number), if not, then a command should have been provided
            try:
                page = int(message)
            except:
                cmd = self.find_command(message)

        if cmd is None:
            embed = self.create_help_embed(page=page)
            msg = await self.bot.say(embed=embed)

            # Add the arrows for previous and next page
            await self.bot.add_reaction(msg, '\N{LEFTWARDS BLACK ARROW}')
            await self.bot.add_reaction(msg, '\N{BLACK RIGHTWARDS ARROW}')
            # The only thing we need to record about this message, is the page number, starting at 1
            self.help_embeds[msg.id] = page
        else:
            # Get the description for a command
            description = cmd.help
            # Split into examples, results, and the description itself based on the string
            example = [x.replace('EXAMPLE: ', '') for x in description.split('\n') if 'EXAMPLE:' in x]
            result = [x.replace('RESULT: ', '') for x in description.split('\n') if 'RESULT:' in x]
            description = [x for x in description.split('\n') if x and 'EXAMPLE:' not in x and 'RESULT:' not in x]
            # Also get the subcommands for this command, if they exist
            subcommands = [x for x in utilities._get_all_commands(cmd) if x != cmd.qualified_name]

            # The rest is simple, create the embed, set the thumbail to me, add all fields if they exist
            embed = discord.Embed(title=cmd.qualified_name)
            embed.set_thumbnail(url=self.bot.user.avatar_url)
            embed.add_field(name="Description", value="\n".join(description), inline=False)
            if example:
                embed.add_field(name="Example", value="\n".join(example), inline=False)
            if result:
                embed.add_field(name="Result", value="\n".join(result), inline=False)
            if subcommands:
                embed.add_field(name='Subcommands', value="\n".join(subcommands), inline=False)

            await self.bot.say(embed=embed)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def motd(self, *, date=None):
        """This command can be used to print the current MOTD (Message of the day)
        This will most likely not be updated every day, however messages will still be pushed to this every now and then

        EXAMPLE: !motd
        RESULT: 'This is an example message of the day!'"""
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

        bot_data = await config.get_content('bot_data')
        total_data = {'member_count': 0,
                      'server_count': 0}
        for entry in bot_data:
            total_data['member_count'] += entry['member_count']
            total_data['server_count'] += entry['server_count']

        # Create the original embed object
        opts = {'title': 'Dev Server',
                'description': 'Join the server above for any questions/suggestions about me.',
                'url': config.dev_server}
        embed = discord.Embed(**opts)

        # Add the normal values
        embed.add_field(name='Total Servers', value=total_data['server_count'])
        embed.add_field(name='Total Members', value=total_data['member_count'])

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

        embed.add_field(name='Uptime', value=(pendulum.utcnow() - self.bot.uptime).in_words())
        embed.set_footer(text=self.bot.description)

        await self.bot.say(embed=embed)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def uptime(self):
        """Provides a printout of the current bot's uptime

        EXAMPLE: !uptime
        RESULT: A BAJILLION DAYS"""
        await self.bot.say("Uptime: ```\n{}```".format((pendulum.utcnow() - self.bot.uptime).in_words()))

    @commands.command(aliases=['invite'])
    @checks.custom_perms(send_messages=True)
    async def addbot(self):
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
        app_info = await self.bot.application_info()
        await self.bot.say("Use this URL to add me to a server that you'd like!\n{}"
                           .format(discord.utils.oauth_url(app_info.id, perms)))

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def doggo(self):
        """Use this to print a random doggo image.

        EXAMPLE: !doggo
        RESULT: A beautiful picture of a dog o3o"""
        # Find a random image based on how many we currently have
        f = random.SystemRandom().choice(glob.glob('images/doggo*'))
        with open(f, 'rb') as f:
            await self.bot.upload(f)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def snek(self):
        """Use this to print a random snek image.

        EXAMPLE: !snek
        RESULT: A beautiful picture of a snek o3o"""
        # Find a random image based on how many we currently have
        f = random.SystemRandom().choice(glob.glob('images/snek*'))
        with open(f, 'rb') as f:
            await self.bot.upload(f)

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def joke(self):
        """Prints a random riddle

        EXAMPLE: !joke
        RESULT: An absolutely terrible joke."""
        # Use the fortune riddles command because it's funny, I promise
        fortune_command = "/usr/bin/fortune riddles"
        while True:
            try:
                fortune = subprocess.check_output(
                    fortune_command.split()).decode("utf-8")
                await self.bot.say(fortune)
            except discord.HTTPException:
                pass
            else:
                break

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
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
        if num <= 1:
            await self.bot.say("A {} sided die? You know that's impossible right?".format(num))
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
