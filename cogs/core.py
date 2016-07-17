from discord.ext import commands
from .utils import config
from .utils import checks
import subprocess
import urllib.parse
import urllib.request
import os
import glob
import json
import random
import discord
import re


class Core:
    """Core commands, these are the not 'complicated' commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.customPermsOrRole("none")
    async def addbot(self):
        """Provides a link that you can use to add me to a server"""
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
        await self.bot.say("Use this URL to add me to a server that you'd like!\n{}"
                           .format(discord.utils.oauth_url('183748889814237186', perms)))
                           
    @commands.command(pass_context=True)
    @checks.customPermsOrRole("none")
    async def doggo(self, ctx):
        """Use this to print a random doggo image.
        Doggo is love, doggo is life."""
        os.chdir('/home/phxntx5/public_html/Bonfire/images')
        f = glob.glob('doggo*')[random.randint(0,len(glob.glob('doggo*'))-1)]
        f = open(f, 'rb')
        await self.bot.send_file(ctx.message.channel,f)
        f.close()

    @commands.command()
    @checks.customPermsOrRole("send_messages")
    async def joke(self):
        """Prints a random riddle"""
        fortuneCommand = "/usr/bin/fortune riddles"
        fortune = subprocess.check_output(fortuneCommand.split()).decode("utf-8")
        await self.bot.say(fortune)

    @commands.command()
    @checks.customPermsOrRole("none")
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
    @checks.customPermsOrRole("none")
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term"""
        if len(search) > 0:
            # This sets the url as url?q=search+terms
            url = 'https://derpibooru.org/search.json?q='
            query = '+'.join(search)
            url += query
            
            nsfw_channels = config.getContent("nsfw_channels")
            if ctx.message.channel.id in nsfw_channels:
                url += ",+explicit&filter_id=95938"
            
            # Get the response from derpibooru and parse the 'searc' result from it
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            results = data['search']
            
            # Get the link if it exists, if not return saying no results found
            if len(results) > 0:
                index = random.randint(0, len(results) - 1)
                imageLink = 'http://' + results[index].get('representations').get('full')[2:].strip()
            else:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            # If no search term was provided, search for a random image
            with urllib.request.urlopen('https://derpibooru.org/images/random') as response:
                imageLink = response.geturl()
        
        # Post link to my link shortening site
        # discord still shows image previews through redirects so this is not an issue.
        url = 'https://shpro.link/redirect.php/'
        data = urllib.parse.urlencode({'link': imageLink}).encode('ascii')
        response = urllib.request.urlopen(url, data).read().decode('utf-8')
        await self.bot.say(response)

    @commands.command(pass_context=True)
    @checks.customPermsOrRole("none")
    async def roll(self, ctx, notation: str="d6"):
        """Rolls a die based on the notation given
        Format should be #d#"""
        try:
            dice = int(re.search("(\d*)d(\d*)", notation).group(1))
            num = int(re.search("(\d*)d(\d*)", notation).group(2))
        # This error will be hit if the notation is completely different than #d#
        except AttributeError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        # This error will be hit if there was an issue converting to an int
        # This means the notation was still given wrong
        except ValueError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        # Dice will be None if d# was provided, assume this means 1d#
        dice = dice or '1'
        if dice > 10:
            await self.bot.say("I'm not rolling more than 10 dice, I have tiny hands")
            return
        if num > 100:
            await self.bot.say("What die has more than 100 sides? Please, calm down")
            return

        valueStr = ", ".join("{}".format(random.randint(1, num)) for i in range(0, int(dice)))

        if int(dice) == 1:
            fmt = '{0.message.author.name} has rolled a {2} sided die and got the number {3}!'
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!'
        await self.bot.say(fmt.format(ctx, dice, num, valueStr))

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    async def tag(self, ctx, *tag: str):
        """This can be used to call custom tags
         The format to call a custom tag is !tag <tag>"""
        tag = ' '.join(tag).strip()
        tags = config.getContent('tags')
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        if len(result) == 0:
            await self.bot.say('That tag does not exist!')
            return
        await self.bot.say("{}".format(result[0]['result']))

    @tag.command(name='add', aliases=['create', 'start'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def add_tag(self, ctx, *result: str):
        """Use this to add a new tag that can be used in this server
        Format to add a tag is !tag add <tag> - <result>"""
        result = ' '.join(result).strip()
        tag = result[0:result.find('-')].strip()
        tag_result = result[result.find('-') + 2:].strip()
        if len(tag) == 0 or len(result) == 0:
            await self.bot.say("Please provide the format for the tag in: !tag add <tag> - <result>")
            return
        tags = config.getContent('tags')
        for t in tags:
            if t['tag'] == tag and t['server_id'] == ctx.message.server.id:
                t['result'] = tag_result
                config.saveContent('tags',tags)
                return
        tags.append({'server_id':ctx.message.server.id,'tag':tag,'result':tag_result})
        config.saveContent('tags',tags)
        await self.bot.say("I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))

    @tag.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.customPermsOrRole("kick_members")
    async def del_tag(self, ctx, *tag: str):
        """Use this to remove a tag that from use for this server
        Format to delete a tag is !tag delete <tag>"""
        tag = ' '.join(tag).strip()
        tags = config.getContent('tags')
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        if len(result) == 0:
            await self.bot.say("The tag {} does not exist! You can't remove something if it doesn't exist...".format(tag))
            return
        for t in tags:
            if t['tag'] == tag and t['server_id'] == ctx.message.server.id:
                tags.remove(t)
                config.saveContent('tags',tags)
        await self.bot.say('I have just removed the tag `{}`'.format(tag))


def setup(bot):
    bot.add_cog(Core(bot))
