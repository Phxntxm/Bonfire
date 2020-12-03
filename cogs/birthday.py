import discord
import datetime
import re
import calendar

from discord.ext import commands, tasks
from asyncpg import UniqueViolationError
import utils


def parse_string(date):
    today = datetime.date.today()
    month = None
    day = None
    month_map = {
        "january": 1,
        "jan": 1,
        "february": 2,
        "feb": 2,
        "march": 3,
        "mar": 3,
        "april": 4,
        "apr": 4,
        "may": 5,
        "june": 6,
        "jun": 6,
        "july": 7,
        "jul": 7,
        "august": 8,
        "aug": 8,
        "september": 9,
        "sep": 9,
        "october": 10,
        "oct": 10,
        "november": 11,
        "nov": 11,
        "december": 12,
        "dec": 12,
    }

    num_re = re.compile(r"^(\d+)[a-z]*$")

    for part in [x.lower() for x in date.split()]:
        match = num_re.match(part)
        if match:
            day = int(match.group(1))
        elif part in month_map:
            month = month_map.get(part)
    if month and day:
        year = today.year
        if month < today.month:
            year += 1
        elif month == today.month and day <= today.day:
            year += 1
        return datetime.date(year, month, day)


class Birthday(commands.Cog):
    """Track and announce birthdays"""

    def __init__(self, bot):
        self.bot = bot
        self.notify_birthdays.start()

    async def get_birthdays_for_server(self, server, today=False):
        query = """
SELECT
    id, birthday
FROM
    users
WHERE
    id=ANY($1::bigint[])
"""
        if today:
            query += """
AND
    birthday = CURRENT_DATE
"""
        query += """
ORDER BY
    birthday
"""

        return await self.bot.db.fetch(query, [m.id for m in server.members])

    @tasks.loop(hours=24)
    async def notify_birthdays(self):
        query = """
SELECT
    id, COALESCE(birthday_alerts, default_alerts) AS channel
FROM
    guilds
WHERE
    birthday_notifications=True
AND
    COALESCE(birthday_alerts, default_alerts) IS NOT NULL
"""
        servers = await self.bot.db.fetch(query)
        update_bds = []
        if not servers:
            return

        for s in servers:
            # Get guild
            g = self.bot.get_guild(s["id"])
            if not g:
                continue
            # Get the channel based on the birthday alerts, or default alerts channel
            channel = g.get_channel(s["channel"])
            if not channel:
                continue

            # Make sure it's chunked
            if not g.chunked:
                await g.chunk()

            bds = await self.get_birthdays_for_server(g, today=True)

            # A list of the id's that will get updated
            for bd in bds:
                try:
                    member = g.get_member(bd["id"])
                    await channel.send(
                        f"It is {member.mention}'s birthday today! "
                        "Wish them a happy birthday! \N{SHORTCAKE}"
                    )
                except (discord.Forbidden, discord.HTTPException):
                    pass
                finally:
                    update_bds.append(bd["id"])

        if not update_bds:
            return

        query = f"""
UPDATE
    users
SET
    birthday = birthday + interval '1 year'
WHERE
    id IN ({", ".join(f"'{bd}'" for bd in update_bds)})
"""
        await self.bot.db.execute(query)

    @notify_birthdays.error
    async def notify_birthdays_errors(self, error):
        await utils.log_error(error, self.bot)

    @commands.group(aliases=["birthdays"], invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def birthday(self, ctx, *, member: discord.Member = None):
        """A command used to view the birthdays on this server; or a specific member's birthday

        EXAMPLE: !birthdays
        RESULT: A printout of the birthdays from everyone on this server"""
        if not ctx.guild.chunked:
            await ctx.guild.chunk()

        if member:
            date = await ctx.bot.db.fetchrow(
                "SELECT birthday FROM users WHERE id=$1", member.id
            )
            if date is None or date["birthday"] is None:
                await ctx.send(f"I do not have {member.display_name}'s birthday saved!")
            else:
                date = date["birthday"]
                await ctx.send(
                    f"{member.display_name}'s birthday is {calendar.month_name[date.month]} {date.day}"
                )
        else:
            # Get this server's birthdays
            bds = await self.get_birthdays_for_server(ctx.guild)
            # Create entries based on the user's display name and their birthday
            entries = [
                f"{ctx.guild.get_member(bd['id']).display_name} ({bd['birthday'].strftime('%B %-d')})"
                for bd in bds
                if bd["birthday"]
            ]
            if not entries:
                await ctx.send("I don't know anyone's birthday in this server!")
                return

            # Create our pages object
            try:
                pages = utils.Pages(ctx, entries=entries, per_page=5)
                pages.title = f"Birthdays for {ctx.guild.name}"
                await pages.paginate()
            except utils.CannotPaginate as e:
                await ctx.send(str(e))

    @birthday.command(name="add")
    @utils.can_run(send_messages=True)
    async def _add_bday(self, ctx, *, date):
        """Used to link your birthday to your account

        EXAMPLE: !birthday add December 1st
        RESULT: I now know your birthday is December 1st"""
        if len(date.split()) != 2:
            await ctx.send(
                "Please provide date in a valid format, such as December 1st!"
            )
            return

        try:
            date = parse_string(date)
        except ValueError:
            await ctx.send(
                "Please provide date in a valid format, such as December 1st!"
            )
            return

        if date is None:
            await ctx.send(
                "Please provide date in a valid format, such as December 1st!"
            )
            return

        await ctx.send(f"I have just saved your birthday as {date}")
        try:
            await ctx.bot.db.execute(
                "INSERT INTO users (id, birthday) VALUES ($1, $2)", ctx.author.id, date
            )
        except UniqueViolationError:
            await ctx.bot.db.execute(
                "UPDATE users SET birthday = $1 WHERE id = $2", date, ctx.author.id
            )

    @birthday.command(name="remove")
    @utils.can_run(send_messages=True)
    async def _remove_bday(self, ctx):
        """Used to unlink your birthday to your account

        EXAMPLE: !birthday remove
        RESULT: I have magically forgotten your birthday"""
        await ctx.send("I don't know your birthday anymore :(")
        await ctx.bot.db.execute(
            "UPDATE users SET birthday=NULL WHERE id=$1", ctx.author.id
        )


def setup(bot):
    bot.add_cog(Birthday(bot))
