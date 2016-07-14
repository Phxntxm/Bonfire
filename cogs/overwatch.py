from .utils import config
from discord.ext import commands

import urllib.parse
import urllib.request
import urllib.error
import asyncio
import json

base_url = "https://owapi.net/api/v2/u/"


class Overwatch:
    def __init__(self, bot):
        self.bot = bot

    @commands.group(no_pm=True, invote_without_command=True)
    async def ow(self):
        pass

    @ow.command(pass_context=True, name="add")
    async def add(self, ctx, username: str):
        username = username.replace("#", "-")
        await self.bot.say("Looking up your profile information....")
        url = base_url + "{}/stats/general".format(username)
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
            cursor.execute('update overwatch set battletag=%s where id=%s', (username, ctx.message.author.id))
            await self.bot.say("I have updated your saved battletag {}".format(ctx.message.author.mention))
        else:
            cursor.execute('insert into overwatch (id, battletag) values (%s, %s)', (ctx.message.author.id, username))
            await self.bot.say("I have just saved your battletag {}".format(ctx.message.author.mention))
        config.closeConnection()

    @ow.command(pass_context=True, name="delete", aliases=['remove'])
    async def delete(self, ctx):
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
