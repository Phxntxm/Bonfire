from discord.ext import commands
from .utils import config
import discord
import subprocess
import urllib.parse
import urllib.request
import json
import random
import discord
import re


class Core:
    """Core commands, these are the not 'complicated' commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
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
                imageLink = 'http://' + results[index].get('representations').get('full')[2:].strip()
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
    async def roll(self, ctx, notation: str = "d6"):
        """Rolls a die based on the notation given
        Format should be #d#"""
        try:
            dice = int(re.search("(\d*)d(\d*)", notation).group(1))
            num = int(re.search("(\d*)d(\d*)", notation).group(2))
        except AttributeError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        except ValueError:
            await self.bot.say("Please provide the die notation in #d#!")
            return
        dice = dice or '1'
        if dice > 10:
            await self.bot.say("I'm not rolling more than 10 dice, I have tiny hands")
            return
        if num > 100:
            await self.bot.say("What die has more than 100 sides? Please, calm down")
            return
        #valueStr = str(random.randint(1, num))
        valueStr += ", ".join("{}".format(random.randint(1, num)) for i in range(1, int(dice)))
        #for i in range(1, int(dice)):
            #value = random.randint(1, num)
            #valueStr += ", {}".format(value)

        if int(dice) == 1:
            fmt = '{0.message.author.name} has rolled a {2} sided die and got the number {3}!'
        else:
            fmt = '{0.message.author.name} has rolled {1}, {2} sided dice and got the numbers {3}!'
        await self.bot.say(fmt.format(ctx, dice, num, valueStr))

    @commands.group(pass_context=True, invoke_without_command=True)
    async def tag(self, ctx, *tag: str):
        """This can be used for custom tags
         The format to call a custom tag is !tag <tag>"""
        tag = ' '.join(tag).strip()
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from tags where server_id=%s and tag=%s', (ctx.message.server.id, tag))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say('That tag does not exist!')
            config.closeConnection()
            return
        await self.bot.say("{}".format(result['result']))
        config.closeConnection()

    @tag.command(name='add', aliases=['create', 'start'], pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def add_tag(self, ctx, *result: str):
        """Use this to add a new tag that can be used in this server
        Format to add a tag is !tag add <tag> - <result>"""
        result = ' '.join(result).strip()
        tag = result[0:result.find('-')]
        result = result[result.find('-') + 2:]
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from tags where server_id=%s and tag=%s', (ctx.message.server.id, tag))
        response = cursor.fetchone()
        if response is not None:
            await self.bot.say('That tag already exists! Please remove it and re-add it!')
            config.closeConnection()
            return
        sql = 'insert into tags (server_id, tag, result) values (%s, %s, %s)'
        cursor.execute(sql, (ctx.message.server.id, tag, result))
        await self.bot.say("I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
        config.closeConnection()

    @tag.command(name='delete', aliases=['remove', 'stop'], pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def del_tag(self, ctx, *tag: str):
        """Use this to remove a tag that from use for this server
        Format to delete a tag is !tag delete <tag>"""
        tag = ' '.join(tag).strip()
        cursor = config.getCursor()
        cursor.execute('use {}'.format(config.db_default))
        cursor.execute('select * from tags where server_id=%s and tag=%s', (ctx.message.server.id, tag))
        result = cursor.fetchone()
        if result is None:
            await self.bot.say("That tag does not exist! You can't remove something if it doesn't exist...")
            config.closeConnection()
            return
        cursor.execute('delete from tags where server_id=%s and tag=%s', (ctx.message.server.id, tag))
        await self.bot.say('I have just removed the tag `{}`'.format(tag))
        config.closeConnection()


def setup(bot):
    bot.add_cog(Core(bot))
