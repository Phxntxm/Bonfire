from discord.ext import commands

from . import utils

from bs4 import BeautifulSoup as bs

import discord
import random
import re
import math


class Links:
    """This class contains all the commands that make HTTP requests
    In other words, all commands here rely on other URL's to complete their requests"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['g'])
    @utils.custom_perms(send_messages=True)
    async def google(self, ctx, *, query: str):
        """Searches google for a provided query

        EXAMPLE: !g Random cat pictures!
        RESULT: Links to sites with random cat pictures!"""
        await ctx.message.channel.trigger_typing()

        url = "https://www.google.com/search"

        # Turn safe filter on or off, based on whether or not this is a nsfw channel
        nsfw = await utils.channel_is_nsfw(ctx.message.channel)
        safe = 'off' if nsfw else 'on'

        params = {'q': query,
                  'safe': safe,
                  'hl': 'en',
                  'cr': 'countryUS'}

        # Our format we'll end up using to send to the channel
        fmt = ""

        # First make the request to google to get the results
        data = await utils.request(url, payload=params, attr='text')

        if data is None:
            await ctx.send("I failed to connect to google! (That can happen??)")
            return

        # Convert to a BeautifulSoup element and loop through each result clasified by h3 tags with a class of 'r'
        soup = bs(data, 'html.parser')

        for element in soup.find_all('h3', class_='r')[:3]:
            # Get the link's href tag, which looks like q=[url here]&sa
            # Use a lookahead and lookbehind to find this url exactly
            try:
                result_url = re.search('(?<=q=).*(?=&sa=)', element.find('a').get('href')).group(0)
            except AttributeError:
                await ctx.send("I couldn't find any results for {}!".format(query))
                return

            # Get the next sibling, find the span where the description is, and get the text from this
            try:
                description = element.next_sibling.find('span', class_='st').text
            except:
                description = ""

            # Add this to our text we'll use to send
            fmt += '\n\n**URL**: <{}>\n**Description**: {}'.format(result_url, description)

        fmt = "**Top 3 results for the query** _{}_:{}".format(query, fmt)
        await ctx.send(fmt)

    @commands.command(aliases=['yt'])
    @utils.custom_perms(send_messages=True)
    async def youtube(self, ctx, *, query: str):
        """Searches youtube for a provided query

        EXAMPLE: !youtube Cat videos!
        RESULT: Cat videos!"""
        await ctx.message.channel.trigger_typing()

        key = utils.youtube_key
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {'key': key,
                  'part': 'snippet, id',
                  'type': 'video',
                  'q': query}

        data = await utils.request(url, payload=params)

        if data is None:
            await ctx.send("Sorry but I failed to connect to youtube!")
            return

        try:
            result = data['items'][0]
        except IndexError:
            await ctx.send("I could not find any results with the search term {}".format(query))
            return

        result_url = "https://youtube.com/watch?v={}".format(result['id']['videoId'])
        title = result['snippet']['title']
        description = result['snippet']['description']

        fmt = "**Title:** {}\n\n**Description:** {}\n\n**URL:** <{}>".format(title, description, result_url)
        await ctx.send(fmt)

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def wiki(self, ctx, *, query: str):
        """Pulls the top match for a specific term from wikipedia, and returns the result

        EXAMPLE: !wiki Test
        RESULT: A link to the wikipedia article for the word test"""
        await ctx.message.channel.trigger_typing()

        # All we need to do is search for the term provided, so the action, list, and format never need to change
        base_url = "https://en.wikipedia.org/w/api.php"
        params = {"action": "query",
                  "list": "search",
                  "format": "json",
                  "srsearch": query}

        data = await utils.request(base_url, payload=params)

        if data is None:
            await ctx.send("Sorry but I failed to connect to Wikipedia!")
            return

        if len(data['query']['search']) == 0:
            await ctx.send("I could not find any results with that term, I tried my best :c")
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

        await ctx.send(
            "Here is the best match I found with the query `{}`:\nURL: <{}>\nSnippet: \n```\n{}```".format(query, url,
                                                                                                           snippet))

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def urban(self, ctx, *, msg: str):
        """Pulls the top urbandictionary.com definition for a term

        EXAMPLE: !urban a normal phrase
        RESULT: Probably something lewd; this is urban dictionary we're talking about"""
        await ctx.message.channel.trigger_typing()

        url = "http://api.urbandictionary.com/v0/define"
        params = {"term": msg}
        try:
            data = await utils.request(url, payload=params)
            if data is None:
                await ctx.send("Sorry but I failed to connect to urban dictionary!")
                return

            # List is the list of definitions found, if it's empty then nothing was found
            if len(data['list']) == 0:
                await ctx.send("No result with that term!")
            # If the list is not empty, use the first result and print it's defintion
            else:
                await ctx.send(data['list'][0]['definition'])
        # Urban dictionary has some long definitions, some might not be able to be sent
        except discord.HTTPException:
            await ctx.send('```\nError: Definition is too long for me to send```')
        except KeyError:
            await ctx.send("Sorry but I failed to connect to urban dictionary!")

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term

        EXAMPLE: !derpi Rainbow Dash
        RESULT: A picture of Rainbow Dash!"""
        await ctx.message.channel.trigger_typing()

        if len(search) > 0:
            url = 'https://derpibooru.org/search.json'

            # Ensure a filter was not provided, as we either want to use our own, or none (for safe pics)
            query = ' '.join(value for value in search if not re.search('&?filter_id=[0-9]+', value))
            params = {'q': query}

            nsfw = await utils.channel_is_nsfw(ctx.message.channel)
            # If this is a nsfw channel, we just need to tack on 'explicit' to the terms
            # Also use the custom filter that I have setup, that blocks some certain tags
            # If the channel is not nsfw, we don't need to do anything, as the default filter blocks explicit
            if nsfw:
                params['q'] += ", (explicit OR suggestive)"
                params['filter_id'] = 95938
            else:
                params['q'] += ", safe"
            # Lets filter out some of the "crap" that's on derpibooru by requiring an image with a score higher than 15
            params['q'] += ', score.gt:15'

            try:
                # Get the response from derpibooru and parse the 'search' result from it
                data = await utils.request(url, payload=params)

                if data is None:
                    await ctx.send("Sorry but I failed to connect to Derpibooru!")
                    return
                results = data['search']
            except KeyError:
                await ctx.send("No results with that search term, {0}!".format(ctx.message.author.mention))
                return

            # The first request we've made ensures there are results
            # Now we can get the total count from that, and make another request based on the number of pages as well
            if len(results) > 0:
                # Get the total number of pages
                pages = math.ceil(data['total'] / len(results))
                # Set a new paramater to set which page to use, randomly based on the number of pages
                params['page'] = random.SystemRandom().randint(1, pages)
                data = await utils.request(url, payload=params)
                if data is None:
                    await ctx.send("Sorry but I failed to connect to Derpibooru!")
                    return
                # Now get the results again
                results = data['search']

                # Get the image link from the now random page'd and random result from that page
                index = random.SystemRandom().randint(0, len(results) - 1)
                image_link = 'https://derpibooru.org/{}'.format(results[index]['id'])
            else:
                await ctx.send("No results with that search term, {0}!".format(ctx.message.author.mention))
                return
        else:
            # If no search term was provided, search for a random image
            # .url will be the URL we end up at, not the one requested.
            # https://derpibooru.org/images/random redirects to a random image, so this is exactly what we want
            image_link = await utils.request('https://derpibooru.org/images/random', attr='url')
        await ctx.send(image_link)

    @commands.command()
    @utils.custom_perms(send_messages=True)
    async def e621(self, ctx, *, tags: str):
        """Searches for a random image from e621.net
        Format for the search terms need to be 'search term 1, search term 2, etc.'
        If the channel the command is ran in, is registered as a nsfw channel, this image will be explicit

        EXAMPLE: !e621 dragon
        RESULT: A picture of a dragon (hopefully, screw your tagging system e621)"""
        await ctx.message.channel.trigger_typing()

        # This changes the formatting for queries, so we don't
        # Have to use e621's stupid formatting when using the command

        tags = tags.replace(' ', '_')
        tags = tags.replace(',_', ' ')

        url = 'https://e621.net/post/index.json'
        params = {'limit': 320,
                  'tags': tags}

        nsfw = await utils.channel_is_nsfw(ctx.message.channel)

        # e621 by default does not filter explicit content, so tack on
        # safe/explicit based on if this channel is nsfw or not
        params['tags'] += " rating:explicit" if nsfw else " rating:safe"

        data = await utils.request(url, payload=params)

        if data is None:
            await ctx.send("Sorry, I had trouble connecting at the moment; please try again later")
            return

        # Try to find an image from the list. If there were no results, we're going to attempt to find
        # A number between (0,-1) and receive an error.
        # The response should be in a list format, so we'll end up getting a key error if the response was in json
        # i.e. it responded with a 404/504/etc.
        try:
            rand_image = data[random.SystemRandom().randint(0, len(data) - 1)]['file_url']
            await ctx.send(rand_image)
        except (ValueError, KeyError):
            await ctx.send("No results with that tag {}".format(ctx.message.author.mention))
            return


def setup(bot):
    bot.add_cog(Links(bot))
