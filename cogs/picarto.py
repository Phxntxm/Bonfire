import asyncio
import discord
import utils

from discord.ext import commands, tasks

BASE_URL = "https://api.picarto.tv/v1"


def produce_embed(*channels):
    description = ""
    # Loop through each channel and produce the information that will go in the description
    for channel in channels:
        url = f"https://picarto.tv/{channel.get('name')}"
        description = f"""{description}\n\n**Title:** [{channel.get("title")}]({url})
**Channel:** [{channel.get("name")}]({url})
**Adult:** {"Yes" if channel.get("adult") else "No"}
**Gaming:** {"Yes" if channel.get("gaming") else "No"}
**Commissions:** {"Yes" if channel.get("commissions") else "No"}"""

    return discord.Embed(
        title="Channels that have gone online!", description=description.strip()
    )


class Picarto(commands.Cog):
    """Pretty self-explanatory"""

    def __init__(self, bot):
        self.bot = bot
        self.channel_info = {}
        self.check_channels.start()

    # noinspection PyAttributeOutsideInit
    async def get_online_users(self):
        # This method is in place to just return all online users so we can compare against it
        url = BASE_URL + "/online"
        payload = {"adult": "true", "gaming": "true"}
        channel_info = {}
        channels = await utils.request(url, payload=payload)
        if channels and isinstance(channels, (list, set, tuple)) and len(channels) > 0:
            for channel in channels:
                name = channel["name"]
                previous = self.channel_info.get(name)
                # There are three statuses, on, remained, and off
                # On means they were off previously, but are now online
                # Remained means they were on previous, and are still on
                # Off means they were on preivous, but are now offline
                # If they weren't included in the online channels...well they're off
                if previous is None:
                    channel_info[name] = channel
                    channel_info[name]["status"] = "on"
                elif previous["status"] in ["on", "remaining"]:
                    channel_info[name] = channel
                    channel_info[name]["status"] = "remaining"
            # After loop has finished successfully, we want to override the statuses of the channels
            self.channel_info = channel_info

    @tasks.loop(seconds=30)
    async def check_channels(self):
        query = """
SELECT
    id, followed_picarto_channels, COALESCE(picarto_alerts, default_alerts) AS channel
FROM
    guilds
WHERE
    COALESCE(picarto_alerts, default_alerts) IS NOT NULL
"""
        # Recheck who is currently online
        await self.get_online_users()
        # Now get all guilds and their picarto channels they follow and loop through them
        results = await self.bot.db.fetch(query) or []
        for result in results:
            # Get all the channels that have gone online
            gone_online = [
                self.channel_info.get(name)
                for name in result["followed_picarto_channels"]
                if self.channel_info.get(name, {}).get("status", "off") == "on"
            ]
            # If they've gone online, produce the embed for them and send it
            if gone_online:
                embed = produce_embed(*gone_online)
                g = self.bot.get_guild(result["id"])
                channel = g.get_channel(result["channel"])
                if channel is not None:
                    try:
                        await channel.send(embed=embed)
                    except (discord.Forbidden, discord.HTTPException, AttributeError):
                        pass

    @check_channels.before_loop
    async def before_check_channels(self):
        await self.get_online_users()
        await asyncio.sleep(30)

    @check_channels.error
    async def picarto_error(self, error):
        await utils.log_error(error, self.bot)
        await self.check_channels.restart()


def setup(bot):
    bot.add_cog(Picarto(bot))
