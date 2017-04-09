from . import utils

from discord.ext import commands
import discord

BASE_URL = "https://api.owapi.net/api/v3/u/"
# This is a list of the possible things that we may want to retrieve from the stats
# The API returns something if it exists, and leaves it out of the data returned entirely if it does not
# For example if you have not won with a character, wins will not exist in the list
# This sets an easy way to use list comprehension later, to print all possible things we want, if it exists
check_g_stats = ["eliminations", "deaths", 'kpd', 'wins', 'losses', 'time_played',
                 'cards', 'damage_done', 'healing_done', 'multikills']
check_o_stats = ['wins']


class Overwatch:
    """Class for viewing Overwatch stats"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def ow(self):
        """Command used to lookup information on your own user, or on another's
        When adding your battletag, it is quite picky, use the exact format user#xxxx
        Multiple names with the same username can be used, this is why the numbers are needed
        Capitalization also matters"""
        pass

    @ow.command(name="stats")
    @utils.custom_perms(send_messages=True)
    async def ow_stats(self, ctx, user: discord.Member = None, hero: str = ""):
        """Prints out a basic overview of a member's stats
        Provide a hero after the member to get stats for that specific hero

        EXAMPLE: !ow stats @OtherPerson Junkrat
        RESULT: Whether or not you should unfriend this person because they're a dirty rat"""
        await ctx.message.channel.trigger_typing()

        user = user or ctx.message.author
        ow_stats = await utils.get_content('overwatch', str(user.id))

        if ow_stats is None:
            await ctx.send("I do not have this user's battletag saved!")
            return
        # This API sometimes takes a while to look up information, so send a message saying we're processing

        bt = ow_stats['battletag']

        if hero == "":
            # If no hero was provided, we just want the base stats for a player
            url = BASE_URL + "{}/stats".format(bt)
            data = await utils.request(url)
            if data is None:
                await ctx.send("I couldn't connect to overwatch at the moment!")
                return

            region = [x for x in data.keys() if data[x] is not None and x in ['us', 'any', 'kr', 'eu']][0]
            stats = data[region]['stats']['quickplay']

            output_data = [(k.title().replace("_", " "), r) for k, r in stats['game_stats'].items() if
                           k in check_g_stats]
        else:
            # If there was a hero provided, search for a user's data on that hero
            hero = hero.lower().replace('-', '')
            url = BASE_URL + "{}/heroes".format(bt)
            data = await utils.request(url)
            if data is None:
                await ctx.send("I couldn't connect to overwatch at the moment!")
                return

            region = [x for x in data.keys() if data[x] is not None][0]
            stats = data[region]['heroes']['stats']['quickplay'].get(hero)

            if stats is None:
                fmt = "I couldn't find data with that hero, make sure that is a valid hero, " \
                      "otherwise {} has never used the hero {} before!".format(user.display_name, hero)
                await ctx.send(fmt)
                return

            # Same list comprehension as before
            output_data = [(k.title().replace("_", " "), r) for k, r in stats['general_stats'].items() if
                           k in check_g_stats]
            for k, r in stats['hero_stats'].items():
                output_data.append((k.title().replace("_", " "), r))
        try:
            banner = await utils.create_banner(user, "Overwatch", output_data)
            await ctx.send(file=banner)
        except (FileNotFoundError, discord.Forbidden):
            fmt = "\n".join("{}: {}".format(k, r) for k, r in output_data)
            await ctx.send("Overwatch stats for {}: ```py\n{}```".format(user.name, fmt))

    @ow.command(pass_context=True, name="add")
    @utils.custom_perms(send_messages=True)
    async def add(self, ctx, bt: str):
        """Saves your battletag for looking up information

        EXAMPLE: !ow add Username#1234
        RESULT: Your battletag is now saved"""
        await ctx.message.channel.trigger_typing()

        # Battletags are normally provided like name#id
        # However the API needs this to be a -, so repliace # with - if it exists
        bt = bt.replace("#", "-")
        key = str(ctx.message.author.id)

        # All we're doing here is ensuring that the status is 200 when looking up someone's general information
        # If it's not, let them know exactly how to format their tag
        url = BASE_URL + "{}/stats".format(bt)
        data = await utils.request(url)
        if data is None:
            await ctx.send("Profile does not exist! Battletags are picky, "
                           "format needs to be `user#xxxx`. Capitalization matters")
            return

        # Now just save the battletag
        entry = {'member_id': key, 'battletag': bt}
        update = {'battletag': bt}
        # Try adding this first, if that fails, update the saved entry
        if not await utils.add_content('overwatch', entry):
            await utils.update_content('overwatch', update, key)
        await ctx.send("I have just saved your battletag {}".format(ctx.message.author.mention))

    @ow.command(pass_context=True, name="delete", aliases=['remove'])
    @utils.custom_perms(send_messages=True)
    async def delete(self, ctx):
        """Removes your battletag from the records

        EXAMPLE: !ow delete
        RESULT: Your battletag is no longer saved"""
        if await utils.remove_content('overwatch', str(ctx.message.author.id)):
            await ctx.send("I no longer have your battletag saved {}".format(ctx.message.author.mention))
        else:
            await ctx.send("I don't even have your battletag saved {}".format(ctx.message.author.mention))


def setup(bot):
    bot.add_cog(Overwatch(bot))
