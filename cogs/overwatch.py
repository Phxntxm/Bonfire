from .utils import config
from .utils import checks
from .utils import images

from discord.ext import commands
import discord

import aiohttp

base_url = "https://api.owapi.net/api/v3/u/"
# This is a list of the possible things that we may want to retrieve from the stats
# The API returns something if it exists, and leaves it out of the data returned entirely if it does not
# For example if you have not won with a character, wins will not exist in the list
# This sets an easy way to use list comprehension later, to print all possible things we want, if it exists
check_g_stats = ["eliminations", "deaths", 'kpd', 'wins', 'losses', 'time_played',
                 'cards', 'damage_done', 'healing_done', 'multikills']
check_o_stats = ['wins']
MAX_RETRIES = 5


class Overwatch:
    """Class for viewing Overwatch stats"""

    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": config.user_agent}
        self.session = aiohttp.ClientSession()

    async def _request(self, payload, endpoint):
        """Handles requesting to the API"""

        # Format the URL we'll need based on the base_url, and the endpoint we want to hit
        url = "{}{}".format(base_url, endpoint)

        # Attempt to connect up to our max retries
        for x in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession().get(url, headers=self.headers, params=payload) as r:
                    # If we failed to connect, attempt again
                    if r.status != 200:
                        continue

                    data = await r.json()
                    return data
            # If any error happened when making the request, attempt again
            except:
                continue

    @commands.group(no_pm=True)
    async def ow(self):
        """Command used to lookup information on your own user, or on another's
        When adding your battletag, it is quite picky, use the exact format user#xxxx
        Multiple names with the same username can be used, this is why the numbers are needed
        Capitalization also matters"""
        pass

    @ow.command(name="stats", pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def ow_stats(self, ctx, user: discord.Member = None, hero: str = ""):
        """Prints out a basic overview of a member's stats
        Provide a hero after the member to get stats for that specific hero

        EXAMPLE: !ow stats @OtherPerson Junkrat
        RESULT: Whether or not you should unfriend this person because they're a dirty rat"""
        user = user or ctx.message.author
        r_filter = {'member_id': user.id}
        ow_stats = await config.get_content('overwatch', r_filter)

        if ow_stats is None:
            await self.bot.say("I do not have this user's battletag saved!")
            return
        # This API sometimes takes a while to look up information, so send a message saying we're processing
        await self.bot.say("Searching profile information....")

        bt = ow_stats[0]['battletag']

        if hero == "":
            # If no hero was provided, we just want the base stats for a player
            data = await self._request(None, "{}/stats/general".format(bt))

            output_data = [(k.title().replace("_", " "), r) for k, r in data['game_stats'].items() if
                           k in check_g_stats]
        else:
            # If there was a hero provided, search for a user's data on that hero
            endpoint = "{}/heroes/{}".format(bt, hero.lower().replace('-', ''))
            data = await self._request(None, endpoint)
            if data is None:
                fmt = "I couldn't find data with that hero, make sure that is a valid hero, " \
                      "otherwise {} has never used the hero {} before!".format(user.display_name, hero)
                await self.bot.say(fmt)
                return

            # Same list comprehension as before
            output_data = [(k.title().replace("_", " "), r) for k, r in data['general_stats'].items() if
                           k in check_g_stats]
            for k, r in data['hero_stats'].items():
                output_data.append((k.title().replace("_", " "), r))
        try:
            banner = await images.create_banner(user, "Overwatch", output_data)
            await self.bot.upload(banner)
        except (FileNotFoundError, discord.Forbidden):
            fmt = "\n".join("{}: {}".format(k, r) for k, r in output_data)
            await self.bot.say("Overwatch stats for {}: ```py\n{}```".format(user.name, fmt))

    @ow.command(pass_context=True, name="add")
    @checks.custom_perms(send_messages=True)
    async def add(self, ctx, bt: str):
        """Saves your battletag for looking up information

        EXAMPLE: !ow add Username#1234
        RESULT: Your battletag is now saved"""
        # Battletags are normally provided like name#id
        # However the API needs this to be a -, so repliace # with - if it exists
        bt = bt.replace("#", "-")
        r_filter = {'member_id': ctx.message.author.id}

        # This API sometimes takes a while to look up information, so send a message saying we're processing
        await self.bot.say("Looking up your profile information....")
        # All we're doing here is ensuring that the status is 200 when looking up someone's general information
        # If it's not, let them know exactly how to format their tag
        endpoint = "{}/stats/general".format(bt)
        data = await self._request(None, endpoint)
        if data is None:
                await self.bot.say("Profile does not exist! Battletags are picky, "
                                   "format needs to be `user#xxxx`. Capitalization matters")
                return

        # Now just save the battletag
        entry = {'member_id': ctx.message.author.id, 'battletag': bt}
        update = {'battletag': bt}
        # Try adding this first, if that fails, update the saved entry
        if not await config.add_content('overwatch', entry, r_filter):
            await config.update_content('overwatch', update, r_filter)
        await self.bot.say("I have just saved your battletag {}".format(ctx.message.author.mention))

    @ow.command(pass_context=True, name="delete", aliases=['remove'])
    @checks.custom_perms(send_messages=True)
    async def delete(self, ctx):
        """Removes your battletag from the records

        EXAMPLE: !ow delete
        RESULT: Your battletag is no longer saved"""
        r_filter = {'member_id': ctx.message.author.id}
        if await config.remove_content('overwatch', r_filter):
            await self.bot.say("I no longer have your battletag saved {}".format(ctx.message.author.mention))
        else:
            await self.bot.say("I don't even have your battletag saved {}".format(ctx.message.author.mention))


def setup(bot):
    bot.add_cog(Overwatch(bot))
