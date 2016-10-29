from .utils import config
from .utils import checks
from .utils import images

from discord.ext import commands
import discord

import aiohttp

# https://github.com/ppy/osu-api/wiki
base_url = 'https://osu.ppy.sh/api/'
MAX_RETRIES = 5

class Osu:
    def __init__(self, bot):
        self.bot = bot
        self.headers = {'User-Agent': config.user_agent}
        self.key = config.osu_key

    async def _request(self, payload, endpoint):
        """Handles requesting to the API"""

        # Format the URL we'll need based on the base_url, and the endpoint we want to hit
        url = "{}{}".format(base_url, endpoint)

        # Check if our key was added, if it wasn't, add it
        key = payload.get('k', self.key)
        payload['k'] = key

        # Attempt to connect up to our max retries
        for x in range(MAX_RETRIES):
            try:
                async with aiohttp.get(url, headers=self.headers, params=payload) as r:
                    # If we failed to connect, attempt again
                    if r.status != 200:
                        continue

                    data = await r.json()
                    return data
            # If any error happened when making the request, attempt again
            except:
                continue

    async def find_beatmap(self, query):
        """Finds a beatmap ID based on the first match of searching a beatmap"""
        pass


    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def osu(self, ctx):
        pass

    @osu.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def osu_user_info(self, ctx, *, user):
        """Used to get information about a specific user
        You can provide either your Osu ID or your username
        However, if your username is only numbers, this will confuse the API
        If you have only numbers in your username, you will need to provide your ID"""

        # A list of the possible values we'll receive, that we want to display
        wanted_info = ['username', 'playcount', 'ranked_score', 'pp_rank', 'level', 'pp_country_rank'
                                  'accuracy', 'country', 'pp_country_rank', 'count_rank_s', 'count_rank_a']

        # A couple of these aren't the best names to display, so setup a map to change these just a little bit
        key_map = {'playcount': 'play_count',
                              'count_rank_ss': 'total_SS_ranks',
                              'count_rank_s': 'total_s_ranks',
                              'count_rank_a': 'total_a_ranks'}

        # The paramaters that we'll send to osu to get the information needed
        params = {'u': user}
        # The endpoint that we're accessing to get this informatin
        endpoint = 'get_user'
        data = await self._request(params, endpoint)

        # Make sure we found a result, we should only find one with the way we're searching
        try:
            data = data[0]
        except IndexError:
            await self.bot.say("I could not find anyone with the user name/id of {}".format(user))
            return

        # Now lets create our dictionary needed to create the image 
        # The dict comprehension we're using is simpler than it looks, it's simply they key: value
        # If the key is in our wanted_info list
        # We also get the wanted value from the key_map if it exists, using the key itself if it doesn't
        # We then title it and replace _ with a space to ensure nice formatting
        fmt = {key_map.get(k, k).title().replace('_', ' '): v for k, v in data.items() if k in wanted_info}

        # Attempt to create our banner and upload that
        # If we can't find the images needed, or don't have permissions, just send a message instead
        try:
            banner = await images.create_banner(ctx.message.author, "Osu User Stats", fmt)
            await self.bot.upload(banner)
        except (FileNotFoundError, discord.Forbidden):
            _fmt = "\n".join("{}: {}".format(k, r) for k, r in fmt.items())
            await self.bot.say("```\n{}```".format(_fmt))

def setup(bot):
    bot.add_cog(Osu(bot))
