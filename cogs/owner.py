from discord.ext import commands

from .utils import config
from .utils import checks

import re
import glob
import discord
import inspect
import aiohttp
import pendulum

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check(checks.is_owner)
    async def motd_push(self, *, message):
        """Used to push a new message to the message of the day"""
        date = pendulum.utcnow().to_date_string()
        r_filter = {'date': date}
        entry = {'motd': message, 'date': date}
        # Try to add this, if there's an entry for that date, lets update it to make sure only one motd is sent a day
        # I should be managing this myself, more than one should not be sent in a day
        if await config.add_content('motd', entry, r_filter):
            await config.update_content('motd', entry, r_filter)
        await self.bot.say("New motd update for {}!".format(date))

    @commands.command()
    @commands.check(checks.is_owner)
    async def running(self):
        """This command detects all things currently running
        This includes music played, tictactoe games, hangman games, and battles"""
        servers_playing_music = len([server_id for server_id, state in self.bot.get_cog('Music').voice_states.items() if
                                     state.is_playing()])
        hm_games = len([server_id for server_id, game in self.bot.get_cog('Hangman').games.items()])
        ttt_games = len([server_id for server_id, game in self.bot.get_cog('TicTacToe').boards.items()])
        count_battles = 0
        for battles in self.bot.get_cog('Interaction').battles.values():
            count_battles += len(battles)
        fmt = ""
        if servers_playing_music:
            fmt += "Playing songs in {} different servers\n".format(servers_playing_music)
        if hm_games:
            fmt += "{} different hangman games running\n".format(hm_games)
        if ttt_games:
            fmt += "{} different TicTacToe games running\n".format(ttt_games)
        if count_battles:
            fmt += "{} different battles going on\n".format(count_battles)

        if not fmt:
            fmt = "Nothing currently running!"
        await self.bot.say(fmt)

    @commands.command()
    @commands.check(checks.is_owner)
    async def adddoggo(self, url: str):
        """Saves a URL as an image to add for the doggo command"""
        # Save the local path based on how many images there currently are
        local_path = 'images/doggo{}.jpg'.format(len(glob.glob('images/doggo*')))

        # "read" the image and save as bytes
        with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                val = await r.read()
                with open(local_path, "wb") as f:
                    f.write(val)
        await self.bot.say(
            "Just saved a new doggo image! I now have {} doggo images!".format(len(glob.glob('images/doggo*'))))

    @commands.command()
    @commands.check(checks.is_owner)
    async def addsnek(self, url: str):
        """Saves a URL as an image to add for the snek command"""
        # Save the local path based on how many images there currently are
        local_path = 'images/snek{}.jpg'.format(len(glob.glob('images/snek*')))

        # "read" the image and save as bytes
        with aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                val = await r.read()
                with open(local_path, "wb") as f:
                    f.write(val)
        await self.bot.say(
            "Just saved a new snek image! I now have {} snek images!".format(len(glob.glob('images/snek*'))))

    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def debug(self, ctx):
        """Executes code"""
        # Eval and exec have different useful purposes, so use both
        try:

            # `Get all content in this format`
            match_single = getter.findall(ctx.message.content)
            # ```\nGet all content in this format```
            match_multi = multi.findall(ctx.message.content)

            if match_single:
                result = eval(match_single[0])

                # In case the result needs to be awaited, handle that
                if inspect.isawaitable(result):
                    result = await result
                await self.bot.say("```\n{0}```".format(result))
            elif match_multi:
                # Internal method to send the message to the channel, of whatever is passed
                def r(v):
                    self.bot.loop.create_task(self.bot.say("```\n{}```".format(v)))

                exec(match_multi[0])
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))

    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def shutdown(self, ctx):
        """Shuts the bot down"""
        fmt = 'Shutting down, I will miss you {0.author.name}'
        await self.bot.say(fmt.format(ctx.message))
        await self.bot.logout()
        await self.bot.close()

    @commands.command()
    @commands.check(checks.is_owner)
    async def avatar(self, content: str):
        """Changes the avatar for the bot to the filename following the command"""
        file = 'images/' + content
        with open(file, 'rb') as fp:
            await self.bot.edit_profile(avatar=fp.read())

    @commands.command()
    @commands.check(checks.is_owner)
    async def name(self, newNick: str):
        """Changes the bot's name"""
        await self.bot.edit_profile(username=newNick)
        await self.bot.say('Changed username to ' + newNick)

    @commands.command()
    @commands.check(checks.is_owner)
    async def status(self, *, status: str):
        """Changes the bot's 'playing' status"""
        await self.bot.change_status(discord.Game(name=status, type=0))
        await self.bot.say("Just changed my status to '{0}'!".format(status))

    @commands.command()
    @commands.check(checks.is_owner)
    async def load(self, *, module: str):
        """Loads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        # This try catch will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await self.bot.say("I have just loaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))

    @commands.command()
    @commands.check(checks.is_owner)
    async def unload(self, *, module: str):
        """Unloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)

        self.bot.unload_extension(module)
        await self.bot.say("I have just unloaded the {} module".format(module))

    @commands.command()
    @commands.check(checks.is_owner)
    async def reload(self, *, module: str):
        """Reloads a module"""

        # Do this because I'm too lazy to type cogs.module
        module = module.lower()
        if not module.startswith("cogs"):
            module = "cogs.{}".format(module)
        self.bot.unload_extension(module)

        # This try block will catch errors such as syntax errors in the module we are loading
        try:
            self.bot.load_extension(module)
            await self.bot.say("I have just reloaded the {} module".format(module))
        except Exception as error:
            fmt = 'An error occurred while processing this request: ```py\n{}: {}\n```'
            await self.bot.say(fmt.format(type(error).__name__, error))


def setup(bot):
    bot.add_cog(Owner(bot))
