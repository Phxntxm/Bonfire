from . import utils

from discord.ext import commands
import discord

# https://github.com/ppy/osu-api/wiki
BASE_URL = 'https://osu.ppy.sh/api/'
MAX_RETRIES = 5


class Osu:
    def __init__(self, bot):
        self.bot = bot
        self.key = utils.osu_key
        self.payload = {'k': self.key}

    async def find_beatmap(self, query):
        """Finds a beatmap ID based on the first match of searching a beatmap"""
        pass

    async def get_beatmap(self, b_id):
        """Gets beatmap info based on the ID provided"""
        payload = self.payload.copy()
        payload['b'] = b_id
        url = BASE_URL + 'get_beatmaps'
        data = await utils.request(url, payload=payload)
        try:
            return data[0]
        except (IndexError, TypeError):
            return None

    @commands.group(invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def osu(self, ctx):
        pass

    @osu.command(name='scores', aliases=['score'])
    @utils.custom_perms(send_messages=True)
    async def osu_user_scores(self, ctx, user, song=1):
        """Used to get the top scores for a user
        You can provide either your Osu ID or your username
        However, if your username is only numbers, this will confuse the API
        If you have only numbers in your username, you will need to provide your ID
        This will by default return the top song, provide song [up to 100] to get that song, in order from best to worst

        EXAMPLE: !osu MyUsername 5
        RESULT: Info about your 5th best song"""

        await ctx.send("Looking up your Osu information...")
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

        payload = self.payload.copy()
        payload['u'] = user
        payload['limit'] = 100
        # The endpoint that we're accessing to get this information
        url = BASE_URL + 'get_user_beat'
        data = await utils.request(url, payload=payload)

        try:
            data = data[song]
        except (IndexError, TypeError):
            if data is not None and len(data) == 0:
                await ctx.send("I could not find any top songs for the user {}".format(user))
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
        fmt = [(key_map.get(k, k).title().replace('_', ' '), v) for k, v in data.items() if k in wanted_info]

        # Attempt to create our banner and upload that
        # If we can't find the images needed, or don't have permissions, just send a message instead
        try:
            banner = await utils.create_banner(ctx.message.author, "Osu User Stats", fmt)
            await self.bot.upload(banner)
        except (FileNotFoundError, discord.Forbidden):
            _fmt = "\n".join("{}: {}".format(k, r) for k, r in fmt)
            await ctx.send("```\n{}```".format(_fmt))

    @osu.command(name='user', pass_context=True)
    @utils.custom_perms(send_messages=True)
    async def osu_user_info(self, ctx, *, user):
        """Used to get information about a specific user
        You can provide either your Osu ID or your username
        However, if your username is only numbers, this will confuse the API
        If you have only numbers in your username, you will need to provide your ID

        EXAMPLE: !osu user MyUserName
        RESULT: Info about your user"""

        await ctx.send("Looking up your Osu information...")
        # A list of the possible values we'll receive, that we want to display
        wanted_info = ['username', 'playcount', 'ranked_score', 'pp_rank', 'level', 'pp_country_rank',
                       'accuracy', 'country', 'pp_country_rank', 'count_rank_s', 'count_rank_a']

        # A couple of these aren't the best names to display, so setup a map to change these just a little bit
        key_map = {'playcount': 'play_count',
                   'count_rank_ss': 'total_SS_ranks',
                   'count_rank_s': 'total_s_ranks',
                   'count_rank_a': 'total_a_ranks'}

        # The paramaters that we'll send to osu to get the information needed
        payload = self.payload.copy()
        payload['u'] = user
        # The endpoint that we're accessing to get this information
        url = BASE_URL + 'get_user'
        data = await utils.request(url, payload=payload)

        # Make sure we found a result, we should only find one with the way we're searching
        try:
            data = data[0]
        except (IndexError, TypeError):
            await ctx.send("I could not find anyone with the user name/id of {}".format(user))
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
            banner = await utils.create_banner(ctx.message.author, "Osu User Stats", fmt)
            await ctx.send(file=banner)
        except (FileNotFoundError, discord.Forbidden):
            _fmt = "\n".join("{}: {}".format(k, r) for k, r in fmt.items())
            await ctx.send("```\n{}```".format(_fmt))


def setup(bot):
    bot.add_cog(Osu(bot))
