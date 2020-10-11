import asyncio
import aiohttp
import traceback

from discord.ext import commands
from base64 import urlsafe_b64encode

import utils


class Spotify(commands.Cog):
    """Pretty self-explanatory"""

    def __init__(self, bot):
        self.bot = bot
        self._token = None
        self._client_id = utils.spotify_id or ""
        self._client_secret = utils.spotify_secret or ""

        self._authorization = "{}:{}".format(self._client_id, self._client_secret)
        self.headers = {
            "Authorization": "Basic {}".format(
                urlsafe_b64encode(self._authorization.encode()).decode()
            )
        }
        self.task = self.bot.loop.create_task(self.api_token_task())

    async def api_token_task(self):
        while True:
            delay = 2400
            try:
                delay = await self.get_api_token()
            except Exception as error:
                with open("error_log", "a") as f:
                    traceback.print_tb(error.__traceback__, file=f)
                    print("{0.__class__.__name__}: {0}".format(error), file=f)
            finally:
                await asyncio.sleep(delay)

    async def get_api_token(self):
        url = "https://accounts.spotify.com/api/token"
        opts = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession(headers=self.headers) as session:
            response = await session.post(url, data=opts)
            data = await response.json()
            self._token = data.get("access_token")
            return data.get("expires_in")

    @commands.group(invoke_without_command=True)
    @utils.can_run(send_messages=True)
    async def spotify(self, ctx, *, query):
        """Searches Spotify for a song, giving you the link you can use to listen in. Give the query to search for
        and it will search by title/artist for the best match

        EXAMPLE: !spotify Eminem
        RESULT: Some Eminem song"""

        # Setup the headers with the token that should be here
        headers = {"Authorization": "Bearer {}".format(self._token)}
        opts = {"q": query, "type": "track"}
        url = "https://api.spotify.com/v1/search"
        response = await utils.request(url, headers=headers, payload=opts)
        try:
            await ctx.send(
                response.get("tracks")
                .get("items")[0]
                .get("external_urls")
                .get("spotify")
            )
        except (KeyError, AttributeError, IndexError):
            await ctx.send("Couldn't find a song for:\n{}".format(query))

    @spotify.command()
    @utils.can_run(send_messages=True)
    async def playlist(self, ctx, *, query):
        """Searches Spotify for a playlist, giving you the link you can use to listen in. Give the query to search for
        and it will search for the best match

        EXAMPLE: !spotify Eminem
        RESULT: Some Eminem song"""
        # Setup the headers with the token that should be here
        headers = {"Authorization": "Bearer {}".format(self._token)}
        opts = {"q": query, "type": "playlist"}
        url = "https://api.spotify.com/v1/search"
        response = await utils.request(url, headers=headers, payload=opts)
        try:
            await ctx.send(
                response.get("playlists")
                .get("items")[0]
                .get("external_urls")
                .get("spotify")
            )
        except (KeyError, AttributeError, IndexError):
            await ctx.send("Couldn't find a song for:\n{}".format(query))


def setup(bot):
    bot.add_cog(Spotify(bot))
