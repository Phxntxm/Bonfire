from discord.ext import commands
from .utils import config
from .utils import checks
import urllib.parse
import urllib.request
import json

class Links:
    """This class contains all the commands that make HTTP requests
    In other words, all commands here rely on other URL's to complete their requests"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.customPermsOrRole("send_messages")
    async def urban(self, *msg: str):
        """Pulls the top urbandictionary.com definition for a term"""
        try:
            url = "http://api.urbandictionary.com/v0/define?term={}".format('+'.join(msg))
            response = urllib.request.urlopen(url)
            data = json.loads(response.read().decode('utf-8'))
            if len(data['list']) == 0:
                await self.bot.say("No result with that term!")
            else:
                await self.bot.say(data['list'][0]['definition'])
        except discord.HTTPException:
            await self.bot.say('```Error: Definition is too long for me to send```')

    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term"""
        if len(search) > 0:
            # This sets the url as url?q=search+terms
            url = 'https://derpibooru.org/search.json?q={}'.format('+'.join(search))

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
                imageLink = 'http://{}'.format(results[index].get('representations').get('full')[2:].strip())
            else:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            # If no search term was provided, search for a random image
            with urllib.request.urlopen('https://derpibooru.org/images/random') as response:
                imageLink = response.geturl()
        await self.bot.say(imageLink)
    
    
    @commands.command(pass_context=True)
    @checks.customPermsOrRole("send_messages")
    async def e621(self, ctx, *, tags: str):
        """Searches for a random image from e621.net
        Format for the search terms need to be 'search term 1, search term 2, etc.'
        If the channel the command is ran in, is registered as a nsfw channel, this image will be explicit"""
        tags = tags.replace(' ', '_')
        tags = tags.replace(',_', '%20')
        url = 'https://e621.net/post/index.json?limit=320&tags={}'.format(tags)
        await self.bot.say("Looking up an image with those tags....")

        if ctx.message.channel.id in config.getContent('nsfw_channels'):
            url += "%20rating:explicit"
        else:
            url += "%20rating:safe"
        request = urllib.request.Request(url, headers={'User-Agent': 'Bonfire/1.0'})
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode('utf-8'))
            if len(data) == 0:
                await self.bot.say("No results with that image {}".format(ctx.message.author.mention))
                return
            elif len(data) == 1:
                rand_image = data[0]['file_url']
            else:
                rand_image = data[random.randint(0, len(data)-1)]['file_url']
            await self.bot.say(rand_image)

def setup(bot):
    bot.add_cog(Links(bot))
