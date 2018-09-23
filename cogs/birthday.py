import discord
import pendulum
import asyncio
import traceback
from pendulum.parsing.exceptions import ParserError

from discord.ext import commands
from . import utils


tzmap = {
    'us-central': pendulum.timezone('US/Central'),
    'eu-central': pendulum.timezone('Europe/Paris'),
    'hongkong': pendulum.timezone('Hongkong'),

}


def sort_birthdays(bds):
    # First sort the birthdays based on the comparison of the actual date
    bds = sorted(bds, key=lambda x: x['birthday'])
    # We want to split this into birthdays after and before todays date
    # We can then use this to sort based on "whose is closest"
    later_bds = []
    previous_bds = []
    # Loop through each birthday
    for bd in bds:
        # If it is after or equal to today, insert into our later list
        if bd['birthday'].date() >= pendulum.today().date():
            later_bds.append(bd)
        # Otherwise, insert into our previous list
        else:
            previous_bds.append(bd)
    # At this point we have 2 lists, in order, one from all of dates before today, and one after
    # So all we need to do is put them in order all of "laters" then all of "befores"
    return later_bds + previous_bds


class Birthday:
    def __init__(self, bot):
        self.bot = bot
        self.task = self.bot.loop.create_task(self.birthday_task())

    def get_birthdays_for_server(self, server, today=False):
        bds = self.bot.db.load('birthdays')
        # Get a list of the ID's to compare against
        member_ids = [str(m.id) for m in server.members]

        # Now create a list comparing to the server's list of member IDs
        bds = [
            bd
            for member_id, bd in bds.items()
            if str(member_id) in member_ids
        ]

        _entries = []

        for bd in bds:
            if not bd['birthday']:
                continue

            day = pendulum.parse(bd['birthday'])
            # tz = tzmap.get(server.region)
            # Check if it's today, and we want to only get todays birthdays
            if (today and day.date() == pendulum.today().date()) or not today:
                # If so, get the member and add them to the entry
                member = server.get_member(int(bd['member_id']))
                _entries.append({
                    'birthday': day,
                    'member': member
                })

        return sort_birthdays(_entries)

    async def birthday_task(self):
        while True:
            try:
                await self.notify_birthdays()
            except Exception as error:
                with open("error_log", 'a') as f:
                    traceback.print_tb(error.__traceback__, file=f)
                    print('{0.__class__.__name__}: {0}'.format(error), file=f)
            finally:
                # Every 12 hours, this is not something that needs to happen often
                await asyncio.sleep(60 * 60 * 12)

    async def notify_birthdays(self):
        tfilter = {'birthdays_allowed': True}
        servers = await self.bot.db.actual_load('server_settings', table_filter=tfilter)
        for s in servers:
            server = self.bot.get_guild(int(s['server_id']))
            if not server:
                continue

            # Set our default to either the one set
            default_channel_id = s.get('notifications', {}).get('default')
            # If it is has been overriden by picarto notifications setting, use this
            channel_id = s.get('notifications', {}).get('birthday') or default_channel_id
            if not channel_id:
                continue

            # Now get the channel based on that ID
            channel = server.get_channel(int(channel_id))

            bds = self.get_birthdays_for_server(server, today=True)
            for bd in bds:
                try:
                    await channel.send("It is {}'s birthday today! "
                                       "Wish them a happy birthday! \N{SHORTCAKE}".format(bd['member'].mention))
                except (discord.Forbidden, discord.HTTPException, AttributeError):
                    pass

    @commands.group(aliases=['birthdays'], invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
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
    @utils.can_run(send_messages=True)
    async def _add_bday(self, ctx, *, date):
        """Used to link your birthday to your account

        EXAMPLE: !birthday add December 1st
        RESULT: I now know your birthday is December 1st"""
        try:
            # Try parsing the date from what was given
            date = pendulum.parse(date)
            # We'll save in a specific way so that it can be parsed how we want, so do this
            date = date.format("%B %-d")
        except (ValueError, ParserError):
            await ctx.send("Please provide date in a valid format, such as December 1st!")
        else:
            entry = {
                'member_id': str(ctx.message.author.id),
                'birthday': date
            }
            await self.bot.db.save('birthdays', entry)
            await ctx.send("I have just saved your birthday as {}".format(date))

    @birthday.command(name='remove')
    @utils.can_run(send_messages=True)
    async def _remove_bday(self, ctx):
        """Used to unlink your birthday to your account

        EXAMPLE: !birthday remove
        RESULT: I have magically forgotten your birthday"""
        entry = {
            'member_id': str(ctx.message.author.id),
            'birthday': None
        }
        await self.bot.db.save('birthdays', entry)
        await ctx.send("I don't know your birthday anymore :(")

    @birthday.command(name='alerts', aliases=['notifications'])
    @commands.guild_only()
    @utils.can_run(manage_guild=True)
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
        await self.bot.db.save('server_settings', entry)
        await ctx.send("All birthday notifications will now go to {}".format(channel.mention))


def setup(bot):
    bot.add_cog(Birthday(bot))
