from discord.ext import commands
from .utils import config
from .utils import checks
import aiohttp
import json
import random
import re

class Links:
    """This class contains all the commands that make HTTP requests
    In other words, all commands here rely on other URL's to complete their requests"""
    
    def __init__(self, bot):
        self.bot = bot
        self.headers = {"User-Agent": "Bonfire/1.0.0"}
        self.session = aiohttp.ClientSession()

    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def wiki(self, *, query: str):
        """Pulls the top match for a specific term, and returns the definition"""
        base_url = "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srsearch="
        async with self.session.get("{}/{}".format(base_url, query), headers=self.headers) as r:
            data = await r.json()
            if len(data['query']['search']) == 0:
                await self.bot.say("I could not find any results with that term, I tried my best :c")
                return
            url = "https://en.wikipedia.org/wiki/{}".format(data['query']['search'][0]['title'].replace(' ', '%20'))
            snippet = data['query']['search'][0]['snippet']
            snippet = re.sub('<span class=\\"searchmatch\\">','', snippet)
            snippet = re.sub('</span>','',snippet)
            snippet = re.sub('&quot;','"',snippet)
        await self.bot.say("Here is the best match I found with the query `{}`:\nURL: {}\n```\nSnippet: {}```".format(query, url, snippet))
        
    @commands.command()
    @checks.custom_perms(send_messages=True)
    async def urban(self, *msg: str):
        """Pulls the top urbandictionary.com definition for a term"""
        url = "http://api.urbandictionary.com/v0/define?term={}".format('+'.join(msg))
        async with self.session.get(url, headers=self.headers) as r:
            response = await r.text()
        data = json.loads(response)
            
        try:
            if len(data['list']) == 0:
                await self.bot.say("No result with that term!")
            else:
                await self.bot.say(data['list'][0]['definition'])
        except discord.HTTPException:
            await self.bot.say('```Error: Definition is too long for me to send```')

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term"""
        if len(search) > 0:
            # This sets the url as url?q=search+terms
            url = 'https://derpibooru.org/search.json?q={}'.format('+'.join(search))
            nsfw_channels = config.get_content("nsfw_channels") or {}
            if ctx.message.channel.id in nsfw_channels:
                url += ",+explicit&filter_id=95938"

            # Get the response from derpibooru and parse the 'search' result from it
            async with self.session.get(url, headers=self.headers) as r:
                response = await r.text()
                    
            data = json.loads(response)
            try:
                results = data['search']
            except KeyError:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return

            # Get the link if it exists, if not return saying no results found
            if len(results) > 0:
                index = random.SystemRandom().randint(0, len(results) - 1)
                imageLink = 'http://{}'.format(results[index].get('representations').get('full')[2:].strip())
            else:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            # If no search term was provided, search for a random image
            async with self.session.get('https://derpibooru.org/images/random') as r:
                imageLink = r.url
        await self.bot.say(imageLink)
    
    
    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def e621(self, ctx, *, tags: str):
        """Searches for a random image from e621.net
        Format for the search terms need to be 'search term 1, search term 2, etc.'
        If the channel the command is ran in, is registered as a nsfw channel, this image will be explicit"""
        tags = tags.replace(' ', '_')
        tags = tags.replace(',_', '%20')
        url = 'https://e621.net/post/index.json?limit=320&tags={}'.format(tags)
        await self.bot.say("Looking up an image with those tags....")

        nsfw_channels = config.get_content("nsfw_channels") or {}
        if ctx.message.channel.id in nsfw_channels:
            url += "%20rating:explicit"
        else:
            url += "%20rating:safe"
            
        async with self.session.get(url, headers=self.headers) as r:
            response = await r.text()
                    
        data = json.loads(response)
        if len(data) == 0:
            await self.bot.say("No results with that image {}".format(ctx.message.author.mention))
            return
        else:
            if len(data) == 1:
                rand_image = data[0]['file_url']
            else:
                rand_image = data[random.SystemRandom().randint(0, len(data)-1)]['file_url']
        await self.bot.say(rand_image)

def setup(bot):
    bot.add_cog(Links(bot))
