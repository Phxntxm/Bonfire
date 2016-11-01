from discord.ext import commands
from .utils import config
from .utils import checks
from bs4 import BeautifulSoup as bs

import discord
import aiohttp
import random
import re
import math
import logging

log = logging.getLogger()

MAX_RETRIES = 5


class Links:
    """This class contains all the commands that make HTTP requests
    In other words, all commands here rely on other URL's to complete their requests"""

    def __init__(self, bot):
        self.bot = bot
        # Only default headers for all requests we should use sets the User-Agent
        self.headers = {"User-Agent": config.user_agent}
        self.session = aiohttp.ClientSession()

    async def _request(self, base_url, payload, endpoint='', convert_json=True):
        """Handles requesting to the API"""

        # Format the URL we'll need based on the base_url, and the endpoint we want to hit
        url = "{}{}".format(base_url, endpoint)

        # Attempt to connect up to our max retries
        for x in range(MAX_RETRIES):
            try:
                async with aiohttp.ClientSession().get(url, headers=self.headers, params=payload) as r:
                    # If we failed to connect, attempt again
                    if r.status != 200:
                        continue

                    if convert_json:
                        data = await r.json()
                    else:
                        data = await r.text()
                    return data
            # If any error happened when making the request, attempt again
            except Exception as e:
                log.error("{0.__class__.__name__}: {0}".format(e))
                continue

    @commands.command(pass_context=True, aliases=['g'])
    @checks.custom_perms(send_messages=True)
    async def google(self, ctx, *, query: str):
        """Searches google for a provided query"""
        url = "https://www.google.com/search"

        # Turn safe filter on or off, based on whether or not this is a nsfw channel
        r_filter = {'channel_id': ctx.message.channel.id}
        nsfw_channels = await config.get_content("nsfw_channels", r_filter)
        safe = 'off' if nsfw_channels else 'on'

        params = {'q': query,
                  'safe': safe,
                  'hl': 'en',
                  'cr': 'countryUS'}

        # Our format we'll end up using to send to the channel
        fmt = ""

        # First make the request to google to get the results
        data = await self._request(url, params, convert_json=False)
        if data is None:
            await self.bot.send_message(ctx.message.channel, "I failed to connect to google! (That can happen??)")
            return

        # Convert to a BeautifulSoup element and loop through each result clasified by h3 tags with a class of 'r'
        soup = bs(data, 'html.parser')

        for element in soup.find_all('h3', class_='r')[:3]:
            # Get the link's href tag, which looks like q=[url here]&sa
            # Use a lookahead and lookbehind to find this url exactly
            try:
                result_url = re.search('(?<=q=).*(?=&sa=)', element.find('a').get('href')).group(0)
            except AttributeError:
                await self.bot.say("I couldn't find any results for {}!".format(query))
                return

            # Get the next sibling, find the span where the description is, and get the text from this
            try:
                description = element.next_sibling.find('span', class_='st').text
            except:
                description = ""

            # Add this to our text we'll use to send
            fmt += '\n\n**URL**: <{}>\n**Description**: {}'.format(result_url, description)

        fmt = "**Top 3 results for the query** _{}_:{}".format(query, fmt)
        await self.bot.say(fmt)

    @commands.command(aliases=['yt'], pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def youtube(self, ctx, *, query: str):
        """Searches youtube for a provided query"""
        key = config.youtube_key
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {'key': key,
                  'part': 'snippet, id',
                  'type': 'video',
                  'q': query}

        data = await self._request(url, params)
        if data is None:
            await self.bot.send_message(ctx.message.channel, "Sorry but I failed to connect to youtube!")
            return

        try:
            result = data['items'][0]
        except IndexError:
            await self.bot.say("I could not find any results with the search term {}".format(query))
            return

        result_url = "https://youtube.com/watch?v={}".format(result['id']['videoId'])
        title = result['snippet']['title']
        description = result['snippet']['description']

        fmt = "**Title:** {}\n\n**Description:** {}\n\n**URL:** <{}>".format(title, description, result_url)
        await self.bot.say(fmt)

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def wiki(self, ctx, *, query: str):
        """Pulls the top match for a specific term, and returns the definition"""
        # All we need to do is search for the term provided, so the action, list, and format never need to change
        base_url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query",
                  "list": "search",
                  "format": "json",
                  "srsearch": query}

        data = await self._request(base_url, params)
        if data is None:
            await self.bot.send_message(ctx.message.channel, "Sorry but I failed to connect to Wikipedia!")
            return

        if len(data['query']['search']) == 0:
            await self.bot.say("I could not find any results with that term, I tried my best :c")
            return
        # Wiki articles' URLs are in the format https://en.wikipedia.org/wiki/[Titlehere]
        # Replace spaces with %20
        url = "https://en.wikipedia.org/wiki/{}".format(data['query']['search'][0]['title'].replace(' ', '%20'))
        snippet = data['query']['search'][0]['snippet']
        # The next part replaces some of the HTML formatting that's provided
        # These are the only ones I've encountered so far through testing, there may be more though
        snippet = re.sub('<span class=\\"searchmatch\\">', '', snippet)
        snippet = re.sub('</span>', '', snippet)
        snippet = re.sub('&quot;', '"', snippet)

        await self.bot.say(
            "Here is the best match I found with the query `{}`:\nURL: <{}>\nSnippet: \n```\n{}```".format(query, url,
                                                                                                           snippet))

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def urban(self, ctx, *, msg: str):
        """Pulls the top urbandictionary.com definition for a term"""
        url = "http://api.urbandictionary.com/v0/define"
        params = {"term": msg}
        try:
            data = await self._request(url, params)
            if data is None:
                await self.bot.send_message(ctx.message.channel, "Sorry but I failed to connect to urban dictionary!")

            # List is the list of definitions found, if it's empty then nothing was found
            if len(data['list']) == 0:
                await self.bot.say("No result with that term!")
            # If the list is not empty, use the first result and print it's defintion
            else:
                await self.bot.say(data['list'][0]['definition'])
        # Urban dictionary has some long definitions, some might not be able to be sent
        except discord.HTTPException:
            await self.bot.say('```\nError: Definition is too long for me to send```')
        except KeyError:
            await self.bot.say("Sorry but I failed to connect to urban dictionary!")

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term"""
        if len(search) > 0:
            url = 'https://derpibooru.org/search.json'

            # Ensure a filter was not provided, as we either want to use our own, or none (for safe pics)
            query = ' '.join(value for value in search if not re.search('&?filter_id=[0-9]+', value))
            params = {'q': query}

            r_filter = {'channel_id': ctx.message.channel.id}
            nsfw_channels = await config.get_content("nsfw_channels", r_filter)
            # If this is a nsfw channel, we just need to tack on 'explicit' to the terms
            # Also use the custom filter that I have setup, that blocks some certain tags
            # If the channel is not nsfw, we don't need to do anything, as the default filter blocks explicit
            if nsfw_channels is not None:
                params['q'] += ", (explicit OR suggestive)"
                params['filter_id'] = 95938
            else:
                params['q'] += ", safe"

            await self.bot.say("Looking up an image with those tags....")

            try:
                # Get the response from derpibooru and parse the 'search' result from it
                data = await self._request(url, params)
                if data is None:
                    await self.bot.send_message(ctx.message.channel, "Sorry but I failed to connect to Derpibooru!")
                    return
                results = data['search']
            except KeyError:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return

            # The first request we've made ensures there are results
            # Now we can get the total count from that, and make another request based on the number of pages as well
            if len(results) > 0:
                pages = math.ceil(data['total'] / len(results))
                params['page'] = random.SystemRandom().randint(1, pages)
                data = await self._request(url, params)
                if data is None:
                    await self.bot.say("Sorry but I failed to connect to Derpibooru!")
                    return
                results = data['search']

                index = random.SystemRandom().randint(0, len(results) - 1)
                image_link = 'https://derpibooru.org/{}'.format(results[index]['id'])
            else:
                await self.bot.say("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            # If no search term was provided, search for a random image
            async with aiohttp.ClientSession().get('https://derpibooru.org/images/random', headers=self.headers) as r:
                # .url will be the URL we end up at, not the one requested.
                # https://derpibooru.org/images/random redirects to a random image, so this is exactly what we want
                image_link = r.url
        await self.bot.say(image_link)

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def e621(self, ctx, *, tags: str):
        """Searches for a random image from e621.net
        Format for the search terms need to be 'search term 1, search term 2, etc.'
        If the channel the command is ran in, is registered as a nsfw channel, this image will be explicit"""

        # This changes the formatting for queries, so we don't
        # Have to use e621's stupid formatting when using the command
        tags = tags.replace(' ', '_')
        tags = tags.replace(',_', ' ')

        url = 'https://e621.net/post/index.json'
        params = {'limit': 320,
                  'tags': tags}
        # e621 provides a way to change how many images can be shown on one request
        # This gives more of a chance of random results, however it causes the lookup to take longer than most
        # Due to this, send a message saying we're looking up the information first
        await self.bot.say("Looking up an image with those tags....")

        r_filter = {'channel_id': ctx.message.channel.id}
        nsfw_channels = await config.get_content("nsfw_channels", r_filter)

        # e621 by default does not filter explicit content, so tack on
        # safe/explicit based on if this channel is nsfw or not
        params['tags'] += " rating:explicit" if nsfw_channels else " rating:safe"

        data = await self._request(url, params)
        if data is None:
            await self.bot.send_message(ctx.message.channel,
                                        "Sorry, I had trouble connecting at the moment; please try again later")
            return

        # Try to find an image from the list. If there were no results, we're going to attempt to find
        # A number between (0,-1) and receive an error.
        # The response should be in a list format, so we'll end up getting a key error if the response was in json
        # i.e. it responded with a 404/504/etc.
        try:
            rand_image = data[random.SystemRandom().randint(0, len(data) - 1)]['file_url']
            await self.bot.say(rand_image)
        except (ValueError, KeyError):
            await self.bot.say("No results with that tag {}".format(ctx.message.author.mention))
            return


def setup(bot):
    bot.add_cog(Links(bot))
