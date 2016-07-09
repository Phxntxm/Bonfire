from discord.ext import commands
from .utils import config
import discord
import subprocess
import urllib.parse
import urllib.request
import json
import random
import discord


class Core:
    """Core commands, these are the not 'complicated' commands."""
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def addbot(self):
        perms = discord.Permissions.none()
        perms.read_messages = True
        perms.send_messages = True
        perms.manage_roles = True
        perms.ban_members = True
        perms.kick_members = True
        perms.manage_messages = True
        perms.embed_links = True
        perms.read_message_history = True
        perms.attach_files = True
        await self.bot.say("Use this URL to add me to a server that you'd like!\n{}'".format(discord.utils.oauth_url('183748889814237186',perms)))
        
    @commands.command()
    async def joke(self):
        """Prints a random riddle"""
        fortuneCommand = "/usr/bin/fortune riddles"
        fortune = subprocess.check_output(fortuneCommand.split()).decode("utf-8")
        await self.bot.say(fortune)

    @commands.command()
    async def urban(self, *msg: str):
        """Pulls the top urbandictionary.com definition for a term"""
        try:
            term = '+'.join(msg)
            url = "http://api.urbandictionary.com/v0/define?term={}".format(term)
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            if len(data['list']) == 0:
                await self.bot.say("No result with that term!")
            else:
                await self.bot.say(data['list'][0]['definition'])
        except discord.HTTPException:
            await self.bot.say('```Error: Definition is too long for me to send```')

    @commands.command(pass_context=True)
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term"""
        if len(search) > 0:
            url = 'https://derpibooru.org/search.json?q='
            query = '+'.join(search)
            url += query
            
            cursor = config.getCursor()
            cursor.execute('use phxntx5_bonfire')
            cursor.execute('select * from nsfw_channels')
            result = cursor.fetchall()
            if {'channel_id': '{}'.format(ctx.message.channel.id)} in result:
                url += ",+explicit&filter_id=95938"
            config.closeConnection()
            
            # url should now be in the form of url?q=search+terms
            # Next part processes the json format, and saves the data in useful lists/dictionaries
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            results = data['search']

            if len(results) > 0:
                index = random.randint(0, len(results) - 1)
                randImageUrl = results[index].get('representations').get('full')[2:]
                randImageUrl = 'http://' + randImageUrl
                imageLink = randImageUrl.strip()
            else:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            with urllib.request.urlopen('https://derpibooru.org/images/random') as response:
                imageLink = response.geturl()
        url = 'https://shpro.link/redirect.php/'
        data = urllib.parse.urlencode({'link': imageLink}).encode('ascii')
        response = urllib.request.urlopen(url, data).read().decode('utf-8')
        await self.bot.say(response)

    @commands.command(pass_context=True)
    async def roll(self, ctx):
        """Rolls a six sided die"""
        num = random.randint(1, 6)
        fmt = '{0.message.author.name} has rolled a die and got the number {1}!'
        await self.bot.say(fmt.format(ctx, num))


def setup(bot):
    bot.add_cog(Core(bot))
