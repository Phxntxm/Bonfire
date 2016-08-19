from cogs.utils import config
from discord.ext import commands
from .utils import checks

from lxml import etree
import aiohttp
import re
import discord
import pendulum
from fuzzywuzzy import process

base_url = "http://api.steampowered.com"
app_id_map = {"portal 2": 620,
              "portal": 400,
              "gmod": 4000,
              "garry's mod": 4000,
              "team fortress 2": 440,
              "tf2": 440,
              "csgo": 430,
              "counter strike: global offensive": 430,
              "css": 240,
              "counter strike: source": 240,
              "cs": 10,
              "counter strike": 10,
              "dota 2": 570,
              "skyrim": 72850,
              "oblivion": 22330,
              "starbound": 211820,
              "terraria": 105600,
              "l4d": 500,
              "left 4 dead": 500,
              "l4d2": 550,
              "left 4 dead 2": 550,
              "xcom 2": 268500,
              "xcom": 200510,
              "ds2": 236430,
              "dark souls 2": 236430,
              "ds3": 374320,
              "dark souls 3": 374320,
              "unturned": 304930,
              "dead island": 91310,
              "dead island 2": 268150,
              "don't starve": 219740,
              "don't starve together": 322330,
              "undertale": 391540,
              "amnesia": 57300,
              "borderlands 2": 49520,
              "borderlands": 8980,
              "soma": 282140,
              "stanley parable": 221910,
              "fallout": 38400,
              "fallout 2": 38410,
              "fallout 3": 22300,
              "fallout 4": 377160,
              "fallout new vegas": 22490
              }
def get_app_id(game: str):
    best_match = process.extractOne(game, app_id_map.keys())[0]
    return app_id_map.get(best_match)
   
class Steam:
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "Bonfire/1.0.0"}
        self.session = aiohttp.ClientSession()
        self.key = config.steam_key

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
    
                
    @commands.group(pass_context=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def steam(self, ctx, member: discord.Member, *option: str):
        """Handles linking/looking information for a certain user
        Call this command by itself with a user, to view some information
        about that user's steam account, if it is linked
        Option can be achievements, games, info and will default to info"""
        # Get the user's steam id if it exists
        try:
            steam_id = config.get_content('steam_users').get(ctx.message.author.id).get('steam_id')
        except AttributeError:
            await self.bot.say("Sorry, but I don't have that user's steam account saved!")
            return
        # Set the url based on which option is provided
        if option[0] == "info":
            url = "{}/ISteamUser/GetPlayerSummaries/v0002/?key={}&steamids={}".format(base_url, self.key, steam_id)
        elif option[0] == "achievements":
            # Attempt to convert the given argument to an int
            # If we can't convert, then an app_id wasn't given, try to find it based on our map of games
            # If the option list doesn't have an index of 1, then no game was given
            try:
                game = " ".join(option[1:])
                if game == "":
                    await self.bot.say("Please provide a game you would like to get the achievements for!")
                    return
                app_id = int(option[1])
            except ValueError:
                app_id = get_app_id(game.lower())
            
            url = "{}/ISteamUserStats/GetPlayerAchievements/v0001/?key={}&steamid={}&appid={}".format(base_url, self.key, steam_id, app_id)
        elif option[0] == "games":
            await self.bot.say("Currently disabled, only achievements and info are available as options")
            return
        
        # Make the request and get the data in json response, all url's we're using will give a json response
        try:
            async with self.session.get(url, headers=self.headers) as response:
                data = await response.json()
        except:
            await self.bot.say("Sorry, I failed looking up that user's information. I'll try better next time ;-;")
            return
        
        if option[0] == "info":
            data = data['response']['players'][0]
            # We need to take into account private profiles, so first add public stuff
            # This maps the number that's returned, to what it means
            status_map = {0: "Offline",
                          1: "Online",
                          2: "Busy",
                          3: "Away",
                          4: "Snooze",
                          5: "Looking to trade",
                          6: "Looking to play"}
            # This is an epoch timestamp for when the user last was "Online"
            # Why this is called 'lastlogoff' I'll never know, ask Steam
            last_seen_date = pendulum.from_timestamp(data.get('lastlogoff'))
            # We want the difference between now and then, to see when they were actually last Online
            # Instead of printing the exact time they were online
            last_seen_delta = pendulum.utcnow() - last_seen_date
            fmt = {"URL": data.get('profileurl'),
                   "Display Name": data.get('personaname'),
                   "Online status": status_map[data.get('personastate')],
                   "Last seen": "{} ago".format(last_seen_delta.in_words())}
            # Now check to see if things exist, and add them to the output if they do
            created_date_timestamp = data.get('timecreated')
            if created_date_timestamp:
                created_date = pendulum.from_timestamp(created_date_timestamp)
                fmt["Signup Date"] = created_date.to_date_string()
            # Going to add if value in here just in case, to ensure no blank content is printed
            fmt_string = "\n".join("{}: {}".format(key, value) for key, value in fmt.items() if value)
            await self.bot.say("```\n{}```".format(fmt_string))
        elif option[0] == 'achievements':
            # First ensure that the profile is not private
            if not data['playerstats']['success']:
                await self.bot.say("Sorry, {} has a private steam account! I cannot lookup their achievements!")
                return
            # Get all achievements for this game
            all_achievements = data['playerstats']['achievements']
            # Now get all achievements that the user has achieved
            successful_achievements = [data for data in all_achievements if data['achieved'] == 1]
            await self.bot.say("{} has achieved {}/{} achievements on the game {}".format(member.display_name, len(successful_achievements), len(all_achievements), game))
        
        
    @steam.command(name='add', aliases=['link', 'create'], pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def add_steam(self, ctx, profile: str):
        """This command can be used to link a steam profile to your user"""
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

        if steam_id is None:
            await self.bot.say("Sorry, couldn't find that Steam user!")
            return
        
        # Save the author's steam ID, ensuring to only overwrite the steam id if they already exist
        author = ctx.message.author
        steam_users = config.get_content('steam_users') or {}
        if steam_users.get(author.id):
            steam_users[author.id]['steam_id'] = steam_id
        else:
            steam_users[author.id] = {'steam_id': steam_id}
        
        config.save_content('steam_users', steam_users)
        await self.bot.say("I have just saved your steam account, you should now be able to view stats for your account!")
        
    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def csgo(self, ctx, member: discord.Member):
        """This command can be used to lookup csgo stats for a user"""
        try:
            steam_id = config.get_content('steam_users').get(ctx.message.author.id).get('steam_id')
        except AttributeError:
            await self.bot.say("Sorry, but I don't have that user's steam account saved!")
            return

        url = "{}/ISteamUserStats/GetUserStatsForGame/v0002/?key={}&appid=730&steamid={}".format(base_url, self.key, steam_id)
        async with self.session.get(url, headers=self.headers) as response:
            data = await response.json()

        stuff_to_print = ['total_kills', 'total_deaths', 'total_wins', 'total_mvps']
        stats = "\n".join(
            "{}: {}".format(d['name'], d['value']) for d in data['playerstats']['stats'] if d['name'] in stuff_to_print)
        await self.bot.say("CS:GO Stats for user {}: \n```\n{}```".format(member.display_name, stats.title().replace("_", " ")))


def setup(bot):
    bot.add_cog(Steam(bot))
