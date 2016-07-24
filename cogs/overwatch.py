from .utils import config
from .utils import checks
from discord.ext import commands
import discord

import aiohttp
import json
import re

base_url = "https://owapi.net/api/v2/u/"
check_g_stats = ["eliminations", "deaths", 'kpd', 'wins', 'losses', 'time_played',
                 'cards', 'damage_done', 'healing_done', 'multikills']
check_o_stats = ['wins', 'losses']


class Overwatch:
    """Class for viewing Overwatch stats"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(no_pm=True)
    async def ow(self):
        pass

    @ow.command(name="stats", pass_context=True, no_pm=True)
    @checks.customPermsOrRole("none")
    async def ow_stats(self, ctx, user: discord.Member=None, hero: str=""):
        """Command used to lookup information on your own user, or on another's
        When adding your battletag, it is quite picky, use the exact format user#xxxx
        Multiple names with the same username can be used, this is why the numbers are needed
        Capitalization also matters"""
        if user is None:
            user = ctx.message.author
        bt = config.getContent('overwatch').get(ctx.message.author.id)

        if bt is None:
            await self.bot.say("I do not have this user's battletag saved!")
            return
        await self.bot.say("Searching profile information....")

        
        if hero == "":
            await aiohttp.ClientSession() as s:
                async with s.get(base_url + "{}/stats/general".format(bt)) as r:
                    result = await r.text()
            
            data = json.loads(result)
            fmt = "\n".join("{}: {}".format(i, r) for i, r in data['game_stats'].items() if i in check_g_stats)
            fmt += "\n"
            fmt += "\n".join("{}: {}".format(i, r) for i, r in data['overall_stats'].items() if i in check_o_stats)
            await self.bot.say(
                "Overwatch stats for {}: ```py\n{}```".format(user.name, fmt.title().replace("_", " ")))
        else:
            url = base_url + "{}/heroes/{}".format(bt, hero.lower().replace('-', '')
            await aiohttp.ClientSession() as s:
                async with s.get(url) as r:
                    if r.status == 500
                        fmt = "{} has not used the hero {} before!".format(user.name, hero.title())
                        await self.bot.say(fmt)
                        return
                    elif r.status = 404
                        fmt = "{} is not an actual hero!".format(hero.title())
                        await self.bot.say(fmt)
                        return
                    result = await r.text() 
            data = json.loads(result)
            
            fmt = "\n".join("{}: {}".format(i, r) for i, r in data['general_stats'].items() if i in check_g_stats)
            fmt += "\n"
            fmt += "\n".join("{}: {}".format(i, r) for i, r in data['hero_stats'].items())
            await self.bot.say("Overwatch stats for {} using the hero {}: ```py\n{}``` "
                               .format(user.name, hero.title(), fmt.title().replace("_", " ")))

    @ow.command(pass_context=True, name="add", no_pm=True)
    @checks.customPermsOrRole("none")
    async def add(self, ctx, bt: str):
        """Saves your battletag for looking up information"""
        bt = bt.replace("#", "-")
        await self.bot.say("Looking up your profile information....")
        url = base_url + "{}/stats/general".format(bt)
        
        await aiohttp.ClientSession() as s:
            async with s.get(url) as r:
                if not r.status == 200:
                    await self.bot.say("Profile does not exist! Battletags are picky, "
                                       "format needs to be `user#xxxx`. Capitalization matters")
                    return
        
        ow = config.getContent('overwatch')
        ow[ctx.message.author.id] = bt
        if config.saveContent('overwatch', ow):
            await self.bot.say("I have just saved your battletag {}".format(ctx.message.author.mention))
        else:
            await self.bot.say("I was unable to save this data")

    @ow.command(pass_context=True, name="delete", aliases=['remove'], no_pm=True)
    @checks.customPermsOrRole("none")
    async def delete(self, ctx):
        """Removes your battletag from the records"""
        result = config.getContent('overwatch')
        if result.get(ctx.message.author.id):
            del result[ctx.message.author.id]
            if config.saveContent('overwatch', result):
                await self.bot.say("I no longer have your battletag saved {}".format(ctx.message.author.mention))
            else:
                await self.bot.say("I was unable to save this data")
        else:
            await self.bot.say("I don't even have your battletag saved {}".format(ctx.message.author.mention))


def setup(bot):
    bot.add_cog(Overwatch(bot))
