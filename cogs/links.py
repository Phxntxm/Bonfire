from discord.ext import commands

import utils

from bs4 import BeautifulSoup as bs

import discord
import re


class Links(commands.Cog):
    """This class contains all the commands that make HTTP requests
    In other words, all commands here rely on other URL's to complete their requests"""

    @commands.command(aliases=["g"])
    @utils.can_run(send_messages=True)
    async def google(self, ctx, *, query: str):
        """Searches google for a provided query

        EXAMPLE: !g Random cat pictures!
        RESULT: Links to sites with random cat pictures!"""
        url = "https://www.google.com/search"

        # Turn safe filter on or off, based on whether or not this is a nsfw channel
        nsfw = utils.channel_is_nsfw(ctx.message.channel)
        safe = "off" if nsfw else "on"

        params = {"q": query, "safe": safe, "hl": "en", "cr": "countryUS"}

        # Our format we'll end up using to send to the channel
        fmt = ""

        # First make the request to google to get the results
        data = await utils.request(url, payload=params, attr="text")

        if data is None:
            await ctx.send("I failed to connect to google! (That can happen??)")
            return

        # Convert to a BeautifulSoup element and loop through each result clasified by h3 tags with a class of 'r'
        soup = bs(data, "html.parser")

        for element in soup.find_all("h3", class_="r")[:3]:
            # Get the link's href tag, which looks like q=[url here]&sa
            # Use a lookahead and lookbehind to find this url exactly
            try:
                result_url = re.search(
                    "(?<=q=).*(?=&sa=)", element.find("a").get("href")
                ).group(0)
            except AttributeError:
                await ctx.send("I couldn't find any results for {}!".format(query))
                return

            # Get the next sibling, find the span where the description is, and get the text from this
            try:
                description = element.next_sibling.find("span", class_="st").text
            except Exception:
                description = ""

            # Add this to our text we'll use to send
            fmt += "\n\n**URL**: <{}>\n**Description**: {}".format(
                result_url, description
            )

        fmt = "**Top 3 results for the query** _{}_:{}".format(query, fmt)
        await ctx.send(fmt)

    @commands.command(aliases=["yt"])
    @utils.can_run(send_messages=True)
    async def youtube(self, ctx, *, query: str):
        """Searches youtube for a provided query

        EXAMPLE: !youtube Cat videos!
        RESULT: Cat videos!"""
        key = utils.youtube_key
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {"key": key, "part": "snippet, id", "type": "video", "q": query}

        data = await utils.request(url, payload=params)

        if data is None:
            await ctx.send("Sorry but I failed to connect to youtube!")
            return

        try:
            result = data["items"][0]
        except IndexError:
            await ctx.send(
                "I could not find any results with the search term {}".format(query)
            )
            return

        result_url = "https://youtube.com/watch?v={}".format(result["id"]["videoId"])
        title = result["snippet"]["title"]
        description = result["snippet"]["description"]

        fmt = "**Title:** {}\n\n**Description:** {}\n\n**URL:** <{}>".format(
            title, description, result_url
        )
        await ctx.send(fmt)

    @commands.command()
    @utils.can_run(send_messages=True)
    async def wiki(self, ctx, *, query: str):
        """Pulls the top match for a specific term from wikipedia, and returns the result

        EXAMPLE: !wiki Test
        RESULT: A link to the wikipedia article for the word test"""
        # All we need to do is search for the term provided, so the action, list, and format never need to change
        base_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "format": "json",
            "srsearch": query,
        }

        data = await utils.request(base_url, payload=params)

        if data is None:
            await ctx.send("Sorry but I failed to connect to Wikipedia!")
            return

        if len(data["query"]["search"]) == 0:
            await ctx.send(
                "I could not find any results with that term, I tried my best :c"
            )
            return
        # Wiki articles' URLs are in the format https://en.wikipedia.org/wiki/[Titlehere]
        # Replace spaces with %20
        url = "https://en.wikipedia.org/wiki/{}".format(
            data["query"]["search"][0]["title"].replace(" ", "%20")
        )
        snippet = data["query"]["search"][0]["snippet"]
        # The next part replaces some of the HTML formatting that's provided
        # These are the only ones I've encountered so far through testing, there may be more though
        snippet = re.sub('<span class=\\"searchmatch\\">', "", snippet)
        snippet = re.sub("</span>", "", snippet)
        snippet = re.sub("&quot;", '"', snippet)

        await ctx.send(
            "Here is the best match I found with the query `{}`:\nURL: <{}>\nSnippet: \n```\n{}```".format(
                query, url, snippet
            )
        )

    @commands.command()
    @utils.can_run(send_messages=True)
    async def urban(self, ctx, *, msg: str):
        """Pulls the top urbandictionary.com definition for a term

        EXAMPLE: !urban a normal phrase
        RESULT: Probably something lewd; this is urban dictionary we're talking about"""
        if utils.channel_is_nsfw(ctx.message.channel):
            url = "http://api.urbandictionary.com/v0/define"
            params = {"term": msg}
            try:
                data = await utils.request(url, payload=params)
                if data is None:
                    await ctx.send("Sorry but I failed to connect to urban dictionary!")
                    return

                # List is the list of definitions found, if it's empty then nothing was found
                if len(data["list"]) == 0:
                    await ctx.send("No result with that term!")
                # If the list is not empty, use the first result and print it's defintion
                else:
                    entries = [x["definition"] for x in data["list"]]
                    try:
                        pages = utils.Pages(ctx, entries=entries[:5], per_page=1)
                        await pages.paginate()
                    except utils.CannotPaginate as e:
                        await ctx.send(str(e))
            # Urban dictionary has some long definitions, some might not be able to be sent
            except discord.HTTPException:
                await ctx.send("```\nError: Definition is too long for me to send```")
            except KeyError:
                await ctx.send("Sorry but I failed to connect to urban dictionary!")
        else:
            await ctx.send("This command is limited to nsfw channels")


def setup(bot):
    bot.add_cog(Links(bot))
