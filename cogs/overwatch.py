from .utils import config
from discord.ext import commands
import discord

import urllib.parse
import urllib.request
import urllib.error
import json

base_url = "https://owapi.net/api/v2/u/"


class Overwatch:
    """Class for viewing Overwatch stats"""
    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, no_pm=True, invote_without_command=True)
    async def ow(self, ctx, user: discord.Member=None, hero: str=""):
        """Command used to lookup information on your own user, or on another's
        When adding your battletag, it is quite picky, use the exact format user#xxxx
        Multiple names with the same username can be used, this is why the numbers are needed
        Capitalization also matters"""
        if user is None:
            user = ctx.message.author
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select battletag from overwatch where id=%s', (user.id,))
        result = cursor.fetchone()
        config.closeConnection()
        if result is None:
            await self.bot.say("I do not have this user's battletag saved!")
            return
        bt = result['battletag']
        await self.bot.say("Searching profile information....")
        if hero == "":
            url = base_url + "{}/stats/general".format(bt)
        else:
            url = base_url + "{}/heroes/{}".format(bt, hero.lower().replace('-', ''))
        result = urllib.request.urlopen(url)
        data = json.loads(result.read().decode('utf-8'))
        if hero == "":
            o_stats = data['overall_stats']
            g_stats = data['game_stats']
        else:
            g_stats = data['general_stats']

        fmt = "Kills: {}".format(int(g_stats['eliminations']))
        fmt += "\nDeaths: {}".format(int(g_stats['deaths']))
        if hero == "":
            fmt += "\nKill/Death Ratio: {}".format(g_stats['kpd'])
            fmt += "\nWins: {}".format(o_stats['wins'])
            fmt += "\nLosses: {}".format(o_stats['losses'])
            d = divmod(g_stats['time_played'], 24)
            fmt += "\nTime Played: {} days {} hours".format(int(d[0]), int(d[1]))
        else:
            fmt += "\nWin Percentage: {}".format(g_stats['win_percentage'])
            fmt += "\nTime Played: {}".format(g_stats['time_played'])
            for i, r in data['hero_stats'].items():
                fmt += "\n{}: {}".format(i.replace("_", " ").title(), r)
        if hero == "":
            await self.bot.say("Overwatch stats for {}: ```py\n{}```".format(user.name, fmt))
        else:
            await self.bot.say("Overwatch stats for {} using the hero {}: ```py\n{}```: ".format(user.name, hero, fmt))

    @ow.command(pass_context=True, name="add")
    async def add(self, ctx, bt: str):
        """Saves your battletag for looking up information"""
        bt = bt.replace("#", "-")
        await self.bot.say("Looking up your profile information....")
        url = base_url + "{}/stats/general".format(bt)
        try:
            urllib.request.urlopen(url)
        except urllib.error.HTTPError:
            await self.bot.say("Profile does not exist! Battletags are picky, "
                               "format needs to be `user#xxxx`. Capitalization matters")
            return
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from overwatch where id=%s', (ctx.message.author.id,))
        result = cursor.fetchone()
        if result:
            cursor.execute('update overwatch set battletag=%s where id=%s', (bt, ctx.message.author.id))
            await self.bot.say("I have updated your saved battletag {}".format(ctx.message.author.mention))
        else:
            cursor.execute('insert into overwatch (id, battletag) values (%s, %s)', (ctx.message.author.id, bt))
            await self.bot.say("I have just saved your battletag {}".format(ctx.message.author.mention))
        config.closeConnection()

    @ow.command(pass_context=True, name="delete", aliases=['remove'])
    async def delete(self, ctx):
        """Removes your battletag from the records"""
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from overwatch where id=%s', (ctx.message.author.id,))
        result = cursor.fetchone()
        if result:
            cursor.execute('delete from overwatch where id=%s', (ctx.message.author.id,))
            await self.bot.say("I no longer have your battletag saved {}".format(ctx.message.author.mention))
        else:
            await self.bot.say("I don't even have your battletag saved {}".format(ctx.message.author.mention))
        config.closeConnection()


def setup(bot):
    bot.add_cog(Overwatch(bot))
