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

    async def get_beatmap(self, b_id):
        """Gets beatmap info based on the ID provided"""
        params = {'b': b_id}
        endpoint = 'get_beatmaps'
        data = await self._request(params, endpoint)
        try:
            return data[0]
        except IndexError:
            return None


    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def osu(self, ctx):
        pass

    @osu.command(name='scores', aliases=['score'], pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def osu_user_scores(self, ctx, user, song=1):
        """Used to get the top scores for a user
        You can provide either your Osu ID or your username
        However, if your username is only numbers, this will confuse the API
        If you have only numbers in your username, you will need to provide your ID
        This will by default return the top song, provide song [up to 100] to get that song, in order from best to worst"""

        # To make this easy for the user, it's indexed starting at 1, so lets subtract by 1
        song -= 1
        # Make sure the song is not negative however, if so set to 0
        if song < 0:
            song = 0

        # A list of the possible values we'll receive, that we want to display
        wanted_info = ['username', 'maxcombo', 'count300', 'count100', 'count50', 'countmiss',
                                   'perfect', 'enabled_mods', 'date', 'rank' 'pp', 'beatmap_title', 'beatmap_version',
                                   'max_combo', 'artist', 'difficulty']

        # A couple of these aren't the best names to display, so setup a map to change these just a little bit
        key_map = {'maxcombo': 'combo',
                              'count300': '300 hits',
                              'count100': '100 hits',
                              'count50': '50 hits',
                              'countmiss': 'misses',
                              'perfect': 'got_max_combo'}

        params = {'u': user,
                            'limit': 100}
        # The endpoint that we're accessing to get this informatin
        endpoint = 'get_user_best'
        data = await self._request(params, endpoint)

        try:
            data = data[song]
        except IndexError:
            if len(data) == 0:
                await self.bot.say("I could not find any top songs for the user {}".format(user))
                return
            else:
                data = data[len(data) - 1]

        # There's a little bit more info that we need, some info specific to the beatmap. 
        # Due to this we'll need to make a second request
        beatmap_data = await self.get_beatmap(data.get('beatmap_id', None))

        # Lets add the extra data we want
        data['beatmap_title'] = beatmap_data.get('title')
        data['beatmap_version'] = beatmap_data.get('version')
        data['max_combo'] = beatmap_data.get('max_combo')
        data['artist'] = beatmap_data.get('artist')
        # Lets round this, no need for such a long number 
        data['difficulty'] = round(float(beatmap_data.get('difficultyrating')), 2)

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

    @osu.command(name='user', pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def osu_user_info(self, ctx, *, user):
        """Used to get information about a specific user
        You can provide either your Osu ID or your username
        However, if your username is only numbers, this will confuse the API
        If you have only numbers in your username, you will need to provide your ID"""

        # A list of the possible values we'll receive, that we want to display
        wanted_info = ['username', 'playcount', 'ranked_score', 'pp_rank', 'level', 'pp_country_rank',
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
