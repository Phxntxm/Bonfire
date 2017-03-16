from . import utils

from discord.ext import commands
import discord

from osuapi import OsuApi, AHConnector

# https://github.com/ppy/osu-api/wiki
BASE_URL = 'https://osu.ppy.sh/api/'
MAX_RETRIES = 5


class Osu:
    def __init__(self, bot):
        self.bot = bot
        self.api = OsuApi(utils.osu_key, connector=AHConnector())
        self.bot.loop.create_task(self.get_users())
        self.osu_users = {}

    async def get_user(self, member, username):
        """A function used to get and save user data in cache"""
        user = self.osu_users.get(member.id)
        if user is None:
            user = await self.get_user_from_api(username)
            if user is not None:
                self.osu_users[member.id] = user
            return user
        else:
            if user.username.lower() == username.lower():
                return user
            else:
                user = await self.get_user_from_api(username)
                if user is not None:
                    self.osu_users[member.id] = user
                return user

    async def get_user_from_api(self, username):
        """A simple helper function to parse the list given and handle failures"""
        user = await self.api.get_user(username)
        try:
            return user[0]
        except IndexError:
            return None

    async def get_users(self):
        """A task used to 'cache' all member's and their Osu profile's"""
        data = await utils.get_content('osu')
        if data is None:
            return

        for result in data:
            member = int(result['member_id'])
            user = await self.get_user_from_api(result['osu_username'])
            if user:
                self.osu_users[member] = user

    @commands.group(invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def osu(self, ctx, member: discord.Member=None):
        """Provides basic information about a specific user

        EXAMPLE: !osu @Person
        RESULT: Informationa bout that person's osu account"""
        if member is None:
            member = ctx.message.author

        user = self.osu_users.get(member.id)
        if user is None:
            await ctx.send("I do not have {}'s Osu user saved!".format(member.display_name))
            return

        e = discord.Embed(title='Osu profile for {}'.format(user.username))
        e.add_field(name='Rank', value="{:,}".format(user.pp_rank))
        e.add_field(name='Level', value=user.level)
        e.add_field(name='Performance Points', value="{:,}".format(user.pp_raw))
        e.add_field(name='Accuracy', value="{:.2%}".format(user.accuracy))
        e.add_field(name='SS Ranks', value="{:,}".format(user.count_rank_ss))
        e.add_field(name='S Ranks', value="{:,}".format(user.count_rank_s))
        e.add_field(name='A Ranks', value="{:,}".format(user.count_rank_a))
        e.add_field(name='Country', value=user.country)
        e.add_field(name='Country Rank', value="{:,}".format(user.pp_country_rank))
        e.add_field(name='Playcount', value="{:,}".format(user.playcount))
        e.add_field(name='Ranked Score', value="{:,}".format(user.ranked_score))
        e.add_field(name='Total Score', value="{:,}".format(user.total_score))

        await ctx.send(embed=e)

    @osu.command(name='add', aliases=['create', 'connect'])
    @utils.custom_perms(send_messages=True)
    async def osu_add(self, ctx, *, username):
        """Links an osu account to your discord account

        EXAMPLE: !osu add username
        RESULT: Links your username to your account, and allows stats to be pulled from it"""
        author = ctx.message.author
        user = await self.get_user(author, username)
        if user is None:
            await ctx.send("I couldn't find an osu user that matches {}".format(username))
            return

        entry = {
            'member_id': str(author.id),
            'osu_username': user.username
        }

        if not await utils.add_content('osu', entry):
            await utils.update_content('osu', entry, str(author.id))

        await ctx.send("I have just saved your Osu user {}".format(author.display_name))

    @osu.command(name='score', aliases=['scores'])
    @utils.custom_perms(send_messages=True)
    async def osu_scores(self, ctx, *data):
        """Find the top x osu scores for a provided member
        Note: You can only get the top 50 songs for a user

        EXAMPLE: !osu scores @Person 5
        RESULT: The top 5 maps for the user @Person"""

        # Set the defaults before we go through our passed data to figure out what we want
        limit = 5
        member = ctx.message.author
        # Only loop through the first 2....we care about nothing after that
        for piece in data[:2]:
            # First lets try to convert to an int, for limit
            try:
                limit = int(piece)
                # Since Osu's API returns no information about the beatmap on scores
                # We also need to call it to get the beatmap...in order to not get rate limited
                # Lets limit this to 50
                if limit > 50:
                    limit = 50
                elif limit < 1:
                    limit = 5
            except:
                converter = commands.converter.MemberConverter()
                converter.prepare(ctx, piece)
                try:
                    member = converter.convert()
                except commands.converter.BadArgument:
                    pass

        user = self.osu_users.get(member.id)
        if user is None:
            await ctx.send("I don't have that user's Osu account saved!")
            return

        scores = await self.api.get_user_best(user.username, limit=limit)
        entries = []
        for i in scores:
            m = await self.api.get_beatmaps(beatmap_id=i.beatmap_id)
            m = m[0]
            entry = {
                'title': 'Top {} Osu scores for {}'.format(limit, member.display_name),
                'fields': [
                    {'name': 'Artist', 'value': m.artist},
                    {'name': 'Title', 'value': m.title},
                    {'name': 'Creator', 'value': m.creator},
                    {'name': 'CS (Circle Size)', 'value': m.diff_size},
                    {'name': 'AR (Approach Rate)', 'value': m.diff_approach},
                    {'name': 'HP (Health Drain)', 'value': m.diff_drain},
                    {'name': 'OD (Overall Difficulty)', 'value': m.diff_overall},
                    {'name': 'Length', 'value': m.total_length},
                    {'name': 'Score', 'value': i.score},
                    {'name': 'Max Combo', 'value': i.maxcombo},
                    {'name': 'Hits', 'value': "{}/{}/{}/{} (300/100/50/misses)".format(i.count300, i.count100, i.count50, i.countmiss), "inline": False},
                    {'name': 'Perfect', 'value': "Yes" if i.perfect else "No"},
                    {'name': 'Rank', 'value': i.rank},
                    {'name': 'PP', 'value': i.pp},
                    {'name': 'Mods', 'value': str(i.enabled_mods)},
                    {'name': 'Date', 'value': str(i.date)}
                ]
            }

            entries.append(entry)
        try:
            pages = utils.DetailedPages(self.bot, message=ctx.message, entries=entries)
            await pages.paginate()
        except utils.CannotPaginate as e:
            await ctx.send(str(e))

def setup(bot):
    bot.add_cog(Osu(bot))
