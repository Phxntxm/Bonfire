from cogs.utils import config
from discord.ext import commands
from .utils import checks

from lxml import etree
import aiohttp
import re
import discord

base_url = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?key={}".format(config.steam_key)


class Steam:
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "Bonfire/1.0.0"}
        self.session = aiohttp.ClientSession()

    async def find_id(self, user: str):
        # Get the profile link based on the user provided, and request the xml data for it
        url = 'http://steamcommunity.com/id/{}/?xml=1'.format(user)
        async with self.session.get(url, headers=self.headers) as response:
            data = await response.text()
            # Remove the xml version content, it breaks etree.fromstring
            data = re.sub('<\?xml.*\?>', '', data)
            tree = etree.fromstring(data)
            # Try to find the steam ID, it will be the first item in the list, so try to convert to an int
            # If it can't be converted to an int, we know that this profile doesn't exist
            # The text will be "The specified profile could not be found." but we don't care about the specific text
            # Through testing, it appears even if a profile is private, the steam ID is still public
            try:
                return int(tree[0].text)
            except ValueError:
                return None

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def csgo(self, ctx, profile: str):
        """This command can be used to lookup csgo stats for a user"""
        # Attempt to find the user/steamid based on the url provided
        # If a url is not provided that matches steamcommunity.com, assume they provided just the user/id
        try:
            user = re.search("((?<=://)?steamcommunity.com/(id|profile)/)+(.*)", profile).group(2)
        except AttributeError:
            user = profile

        # To look up userdata, we need the steam ID. Try to convert to an int, if we can, it's the steam ID
        # If we can't convert to an int, use our method to find the steam ID for a certain user
        try:
            steam_id = int(user)
        except ValueError:
            steam_id = await self.find_id(user)

        await self.bot.say("User given was: {}\nFound steam_id: {}".format(user, steam_id))

        if steam_id is None:
            await self.bot.say("Sorry, couldn't find that Steam user!")
            return

        url = "{}&appid=730&steamid={}".format(base_url, steam_id)
        async with self.session.get(url, headers=self.headers) as response:
            data = await response.json()

        stuff_to_print = ['total_kills', 'total_deaths', 'total_wins', 'total_mvps']
        stats = "\n".join(
            "{}: {}".format(d['name'], d['value']) for d in data['playerstats']['stats'] if d['name'] in stuff_to_print)
        await self.bot.say("CS:GO Stats for user {}: \n```\n{}```".format(user, stats))


def setup(bot):
    bot.add_cog(Steam(bot))
