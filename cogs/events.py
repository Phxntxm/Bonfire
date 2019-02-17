from utils import config
import aiohttp
import logging
import json
import discord

log = logging.getLogger()

discord_bots_url = 'https://bots.discord.pw/api/bots/{}/stats'
discordbots_url = "https://discordbots.org/api/bots/{}/stats"
carbonitex_url = 'https://www.carbonitex.net/discord/data/botdata.php'


class StatsUpdate:
    """This is used purely to update stats information for the bot sites"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def __unload(self):
        self.bot.loop.create_task(self.session.close())

    async def update(self):
        server_count = len(self.bot.guilds)

        # Carbonitex request
        carbon_payload = {
            'key': config.carbon_key,
            'servercount': server_count
        }

        async with self.session.post(carbonitex_url, data=carbon_payload) as resp:
            log.info('Carbonitex statistics returned {} for {}'.format(resp.status, carbon_payload))

        # Discord.bots.pw request
        payload = json.dumps({
            'server_count': server_count
        })

        headers = {
            'authorization': config.discord_bots_key,
            'content-type': 'application/json'
        }

        url = discord_bots_url.format(self.bot.user.id)
        async with self.session.post(url, data=payload, headers=headers) as resp:
            log.info('bots.discord.pw statistics returned {} for {}'.format(resp.status, payload))

        # discordbots.com request
        url = discordbots_url.format(self.bot.user.id)
        payload = {
            "server_count": server_count
        }

        headers = {
            "Authorization": config.discordbots_key
        }
        async with self.session.post(url, data=payload, headers=headers) as resp:
            log.info('discordbots.com statistics retruned {} for {}'.format(resp.status, payload))

    async def on_guild_join(self, _):
        await self.update()

    async def on_guild_leave(self, _):
        await self.update()

    async def on_ready(self):
        await self.update()

    async def on_member_join(self, member):
        query = """
SELECT
    COALESCE(welcome_alerts, default_alerts) AS channel,
    welcome_msg AS msg,
    join_role as role,
    welcome_notifications as notify
FROM
    guilds
WHERE
    id = $1
"""
        settings = await self.bot.db.fetchrow(query, member.guild.id)
        if settings:
            message = settings['msg'] or "Welcome to the '{server}' server {member}!"
            if settings["notify"]:
                try:
                    channel = member.guild.get_channel(settings['channel'])
                    await channel.send(message.format(server=member.guild.name, member=member.mention))
                    # Forbidden for if the channel has send messages perms off
                    # HTTP Exception to catch any weird happenings
                    # Attribute Error catches when a channel is set, but that channel doesn't exist any more
                except (discord.Forbidden, discord.HTTPException, AttributeError):
                    pass

            try:
                role = member.guild.get_role(settings['role'])
                await member.add_roles(role)
            except (discord.Forbidden, discord.HTTPException, AttributeError):
                pass

    async def on_member_remove(self, member):
        query = """
SELECT
    COALESCE(goodbye_alerts, default_alerts) AS channel,
    goodbye_msg AS msg
FROM
    guilds
WHERE
    goodbye_notifications = True
AND
    id = $1
AND
    COALESCE(goodbye_alerts, default_alerts) IS NOT NULL
"""
        settings = await self.bot.db.fetchrow(query, member.guild.id)
        if settings:
            message = settings['msg'] or "{member} has left the server, I hope it wasn't because of something I said :c"
            channel = member.guild.get_channel(settings['channel'])
            try:
                await channel.send(message.format(server=member.guild.name, member=member.mention))
            except (discord.Forbidden, discord.HTTPException, AttributeError):
                pass


def setup(bot):
    bot.add_cog(StatsUpdate(bot))
