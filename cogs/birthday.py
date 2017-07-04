import discord
import pendulum
from pendulum.parsing.exceptions import ParserError

from discord.ext import commands
from . import utils

class Birthday:

    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.birthday_task())

    def get_birthdays_for_server(self, server, today=False):
        bds = self.bot.db.load('birthdays')
        # Get a list of the ID's to compare against
        member_ids = [str(m.id) for m in server.members]

        # Now create a list comparing to the server's list of member IDs
        bds = [x for x in bds if x['member_id'] in member_ids]

        _entries = []

        for bd in bds:
            if not bd['birthday']:
                continue

            day = pendulum.parse(bd['birthday'])
            # Check if it's today, and we want to only get todays birthdays
            if (today and day.date() == pendulum.today().date()) or not today:
                # If so, get the member and add them to the entry
                member = server.get_member(int(bd['member_id']))
                _entries.append({
                    'birthday': day,
                    'member': member
                })

        return _entries

    async def birthday_task(self):
        while True:
            await self.notify_birthdays()
            # Every 12 hours, this is not something that needs to happen often
            await asyncio.sleep(60 * 60 * 12)

    async def notify_birthdays(self):
        tfilter = {'birthdays_allowed': True}
        servers = await self.bot.db.actual_load('server_settings', table_filter=tfilter)
        for s in servers:
            server = bot.get_guild(int(s['server_id']))
            if not server:
                continue

            bds = self.get_birthdays_for_server(server, today=True)
            for bd in bds:
                # Set our default to either the one set, or the default channel of the server
                default_channel_id = servers.get('notifications', {}).get('default') or guild.id
                # If it is has been overriden by picarto notifications setting, use this
                channel_id = servers.get('notifications', {}).get('birthdays') or default_channel_id
                # Now get the channel based on that ID
                channel = server.get_channel(int(channel_id)) or server.default_channel
                try:
                    await channel.send("It is {}'s birthday today! Wish them a happy birthday! \N{SHORTCAKE}".format(member.mention))
                except (discord.Forbidden, discord.HTTPException):
                    pass

    @commands.group(aliases=['birthdays'], invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def birthday(self, ctx, *, member: discord.Member = None):
        """A command used to view the birthdays on this server; or a specific member's birthday

        EXAMPLE: !birthdays
        RESULT: A printout of the birthdays from everyone on this server"""
        if member:
            date = self.bot.db.load('birthdays', key=member.id, pluck='birthday')
            if date:
                await ctx.send("{}'s birthday is {}".format(member.display_name, date))
            else:
                await ctx.send("I do not have {}'s birthday saved!".format(member.display_name))
        else:
            # Get this server's birthdays
            bds = self.get_birthdays_for_server(ctx.message.guild)
            # Create entries based on the user's display name and their birthday
            entries = ["{} ({})".format(bd['member'].display_name, bd['birthday'].format("%B %-d")) for bd in bds]
            # Create our pages object
            try:
                pages = utils.Pages(self.bot, message=ctx.message, entries=entries, per_page=5)
                pages.title = "Birthdays for {}".format(ctx.message.guild.name)
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))


    @birthday.command(name='add')
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def _add_bday(self, ctx, *, date):
        """Used to link your birthday to your account

        EXAMPLE: !birthday add December 1st
        RESULT: I now know your birthday is December 1st"""
        try:
            # Try parsing the date from what was given
            date = pendulum.parse(date)
            # We'll save in a specific way so that it can be parsed how we want, so do this
            date = date.format("%B %-d")
        except ParserError:
            await ctx.send("Please provide date in a valid format, such as December 1st!")
        else:
            entry = {
                'member_id': str(ctx.message.author.id),
                'birthday': date
            }
            self.bot.db.save('birthdays', entry)
            await ctx.send("I have just saved your birthday as {}".format(date))

    @birthday.command(name='remove')
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def _remove_bday(self, ctx):
        """Used to unlink your birthday to your account

        EXAMPLE: !birthday remove
        RESULT: I have magically forgotten your birthday"""
        entry = {
            'member_id': str(ctx.message.author.id),
            'birthday': None
        }
        self.bot.db.save('birthdays', entry)
        await ctx.send("I don't know your birthday anymore :(")

    @birthday.command(name='alerts', aliases=['notifications'])
    @commands.guild_only()
    @utils.custom_perms(manage_guild=True)
    @utils.check_restricted()
    async def birthday_alerts_channel(self, ctx, channel: discord.TextChannel):
        """Sets the notifications channel for birthday notifications

        EXAMPLE: !birthday alerts #birthday
        RESULT: birthday notifications will go to this channel
        """
        entry = {
            'server_id': str(ctx.message.guild.id),
            'notifications': {
                'birthday': str(channel.id)
            }
        }
        self.bot.db.save('server_settings', entry)
        await ctx.send("All birthday notifications will now go to {}".format(channel.mention))

def setup(bot):
    bot.add_cog(Birthday(bot))
