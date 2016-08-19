from discord.ext import commands
from .utils import config
from .utils import checks
import re
import os
import glob
import sys
import discord
import inspect
import aiohttp

getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Owner:
    """Commands that can only be used by Phantom, bot management commands"""

    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    @commands.check(checks.is_owner)
    async def testcommand(self, member: discord.Member):
        role = [discord.Role(id="183749087038930944"), discord.Object(id="183749087038930944")]
        await self.bot.add_roles(member, *roles)
        await self.bot.say("Just added the roles {} to {}".format(role, member.display_name))
        
    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def saferestart(self, ctx):
        """This commands is used to check if there is anything playing in any servers at the moment
        If there is, I'll tell you not to restart, if not I'll just go ahead and restart"""
        # I do not want to restart the bot if someone is playing music 
        # This gets all the exiting VoiceStates that are playing music right now
        # If we are, say which server it 
        servers_playing_music = [server_id for server_id, state in self.bot.get_cog('Music').voice_states.items() if
                                 state.is_playing()]
        if len(servers_playing_music) > 0:
            await self.bot.say("Sorry, it's not safe to restart. I am currently playing a song on {} servers".format(
                len(servers_playing_music)))
        else:
            config.save_content('restart_server', ctx.message.channel.id)
            await self.bot.say("Restarting; see you in the next life {0}!".format(ctx.message.author.mention))
            python = sys.executable
            os.execl(python, python, *sys.argv)

    @commands.command(pass_context=True)
    @commands.check(checks.is_owner)
    async def restart(self, ctx):
        """Forces the bot to restart"""
        # This command is left in so that we can invoke it from saferestart, or we need a restart no matter what
        config.save_content('restart_server', ctx.message.channel.id)
        await self.bot.say("Restarting; see you in the next life {0}!".format(ctx.message.author.mention))
        python = sys.executable
        os.execl(python, python, *sys.argv)

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
