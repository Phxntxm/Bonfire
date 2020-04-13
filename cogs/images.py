from discord.ext import commands
import discord
import itertools
import random
import re
import math

import utils


class Images(commands.Cog):
    """Commands that post images, or look up images"""

    async def horse_noodle_api(self, ctx, animal):
        data = await utils.request(f"http://hrsendl.com/api/{animal}")

        try:
            url = data["data"]["file_url_size_large"]
            filename = data["data"]["file_name"]
        except (KeyError, TypeError):
            return await ctx.send(f"I couldn't connect! Sorry no {animal}s right now ;w;")
        else:
            image = await utils.download_image(url)
            f = discord.File(image, filename=filename)
            try:
                await ctx.send(file=f)
            except discord.HTTPException:
                await ctx.send(
                    f"File to large to send as attachment, here is the URL: {url}"
                )

    @commands.command(aliases=['rc'])
    @utils.can_run(send_messages=True)
    async def cat(self, ctx):
        """Use this to print a random cat image.

        EXAMPLE: !cat
        RESULT: A beautiful picture of a cat o3o"""
        url = "http://thecatapi.com/api/images/get"
        opts = {"format": "src"}
        result = await utils.request(url, attr='url', payload=opts)

        try:
            image = await utils.download_image(result)
        except (ValueError, AttributeError):
            await ctx.send("I couldn't connect! Sorry no cats right now ;w;")

        f = discord.File(image, filename=result.name)
        try:
            await ctx.send(file=f)
        except discord.HTTPException:
            await ctx.send(
                f"File to large to send as attachment, here is the URL: {url}"
            )

    @commands.command(aliases=['dog', 'rd'])
    @utils.can_run(send_messages=True)
    async def doggo(self, ctx):
        """Use this to print a random doggo image.

        EXAMPLE: !doggo
        RESULT: A beautiful picture of a dog o3o"""
        result = await utils.request('https://random.dog/woof.json')
        try:
            url = result.get("url")
            filename = re.match("https://random.dog/(.*)", url).group(1)
        except AttributeError:
            await ctx.send("I couldn't connect! Sorry no dogs right now ;w;")
            return

        image = await utils.download_image(url)
        f = discord.File(image, filename=filename)
        try:
            await ctx.send(file=f)
        except discord.HTTPException:
            await ctx.send(
                f"File to large to send as attachment, here is the URL: {url}"
            )

    @commands.command(aliases=['snake'])
    @utils.can_run(send_messages=True)
    async def snek(self, ctx):
        """Use this to print a random snek image.

        EXAMPLE: !snek
        RESULT: A beautiful picture of a snek o3o"""
        await self.horse_noodle_api(ctx, "snake")

    @commands.command()
    @utils.can_run(send_messages=True)
    async def horse(self, ctx):
        """Use this to print a random horse image.

        EXAMPLE: !horse
        RESULT: A beautiful picture of a horse o3o"""
        await self.horse_noodle_api(ctx, "horse")

    @commands.command()
    @utils.can_run(send_messages=True)
    async def duck(self, ctx):
        """Use this to print a random duck image.

        EXAMPLE: !duck
        RESULT: A beautiful picture of a duck o3o"""
        await self.horse_noodle_api(ctx, "duck")

    @commands.command()
    @utils.can_run(send_messages=True)
    async def snail(self, ctx):
        """Use this to print a random snail image.

        EXAMPLE: !snail
        RESULT: A beautiful picture of a snail o3o"""
        await self.horse_noodle_api(ctx, "snail")

    @commands.command()
    @utils.can_run(send_messages=True)
    async def pleco(self, ctx):
        """Use this to print a random pleco image.

        EXAMPLE: !pleco
        RESULT: A beautiful picture of a pleco o3o"""
        await self.horse_noodle_api(ctx, "pleco")

    @commands.command()
    @utils.can_run(send_messages=True)
    async def moth(self, ctx):
        """Use this to print a random moth image.

        EXAMPLE: !moth
        RESULT: A beautiful picture of a moth o3o"""
        await self.horse_noodle_api(ctx, "moth")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def avatar(self, ctx, member: discord.Member = None):
        """Provides an image for the provided person's avatar (yours if no other member is provided)

        EXAMPLE: !avatar @person
        RESULT: A full image of that person's avatar"""

        if member is None:
            member = ctx.message.author

        url = str(member.avatar_url)
        if '.gif' not in url:
            url = str(member.avatar_url_as(format='png'))
            filename = 'avatar.png'
        else:
            filename = 'avatar.gif'
        if ctx.message.guild.me.permissions_in(ctx.message.channel).attach_files:
            filedata = await utils.download_image(url)
            if filedata is None:
                await ctx.send(url)
            else:
                try:
                    f = discord.File(filedata, filename=filename)
                    await ctx.send(file=f)
                except discord.HTTPException:
                    await ctx.send("Sorry but that avatar is too large for me to send!")
        else:
            await ctx.send(url)

    @commands.command()
    @utils.can_run(send_messages=True)
    async def derpi(self, ctx, *search: str):
        """Provides a random image from the first page of derpibooru.org for the following term

        EXAMPLE: !derpi Rainbow Dash
        RESULT: A picture of Rainbow Dash!"""

        if len(search) > 0:
            url = 'https://derpibooru.org/search.json'

            # Ensure a filter was not provided, as we either want to use our own, or none (for safe pics)
            query = ' '.join(value for value in search if not re.search('&?filter_id=[0-9]+', value))
            params = {'q': query}

            nsfw = utils.channel_is_nsfw(ctx.message.channel)
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
                # image_link = 'https://derpibooru.org/{}'.format(results[index]['id'])
                image_link = 'https:{}'.format(results[index]['image'])
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
    @utils.can_run(send_messages=True)
    async def e621(self, ctx, *, tags: str):
        """Searches for a random image from e621.net
        Format for the search terms need to be 'search term 1, search term 2, etc.'
        If the channel the command is ran in, is registered as a nsfw channel, this image will be explicit

        EXAMPLE: !e621 dragon
        RESULT: A picture of a dragon (hopefully, screw your tagging system e621)"""

        # This changes the formatting for queries, so we don't
        # Have to use e621's stupid formatting when using the command

        tags = tags.replace(' ', '_')
        tags = tags.replace(',_', ' ')

        url = 'https://e621.net/posts.json'
        params = {
            'login': utils.config.e621_user,
            'api_key': utils.config.e621_key,
            'limit': 5,
            'tags': tags
        }
        headers = {'User-Agent': utils.config.user_agent}
        nsfw = utils.channel_is_nsfw(ctx.message.channel)

        # e621 by default does not filter explicit content, so tack on
        # safe/explicit based on if this channel is nsfw or not
        params['tags'] += " rating:explicit" if nsfw else " rating:safe"
        # Tack on a random order
        params['tags'] += " order:random"

        data = await utils.request(url, payload=params, headers=headers)

        if data is None:
            await ctx.send("Sorry, I had trouble connecting at the moment; please try again later")
            return

        # Try to find an image from the list. If there were no results, we're going to attempt to find
        # A number between (0,-1) and receive an error.
        # The response should be in a list format, so we'll end up getting a key error if the response was in json
        # i.e. it responded with a 404/504/etc.
        try:
            for image in data["posts"]:
                # Will support in the future
                blacklist = []
                tags = itertools.chain.from_iterable(image["tags"].values())
                # Check if any of the tags are in the blacklist
                if any(tag in tags for tag in blacklist):
                    continue
                # If this image is fine, then send this and break
                await ctx.send(image["file"]["url"])
                return
        except (ValueError, KeyError):
            await ctx.send("No results with that tag {}".format(ctx.message.author.mention))
            return


def setup(bot):
    bot.add_cog(Images(bot))
