from discord.ext import commands
import discord

from .utils import config
from .utils import checks

import aiohttp
import re
import json
import pendulum


def setup(bot):
    bot.add_cog(Strawpoll(bot))


getter = re.compile(r'`(?!`)(.*?)`')
multi = re.compile(r'```(.*?)```', re.DOTALL)


class Strawpoll:
    """This class is used to create new strawpoll """

    def __init__(self, bot):
        self.bot = bot
        self.url = 'https://strawpoll.me/api/v2/polls'
        self.headers = {'User-Agent': 'Bonfire/1.0.0',
                        'Content-Type': 'application/json'}
        self.session = aiohttp.ClientSession()

    @commands.group(aliases=['strawpoll', 'poll', 'polls'], pass_context=True, invoke_without_command=True)
    @checks.customPermsOrRole(send_messages=True)
    async def strawpolls(self, ctx, poll_id: str = None):
        """This command can be used to show a strawpoll setup on this server"""
        all_polls = config.getContent('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}
        if not server_polls:
            await self.bot.say("There are currently no strawpolls running on this server!")
            return
        if not poll_id:
            fmt = "\n".join(
                "{}: https://strawpoll.me/{}".format(data['title'], _id) for _id, data in server_polls.items())
            await self.bot.say("```\n{}```".format(fmt))
        elif poll_id in server_polls.keys():
            poll = server_polls[poll_id]

            async with self.session.get("{}/{}".format(self.url, poll_id)) as response:
                data = await response.json()

            fmt_options = "\n\t".join(
                "{}: {}".format(r, data['votes'][i]) for i, r in enumerate(data['options']))
            author = discord.utils.get(self.bot.get_all_members(), id=poll['author'])
            created_ago = (pendulum.utcnow() - pendulum.parse(poll['date'])).in_words()
            link = "https://strawpoll.me/{}".format(poll_id)
            fmt = "Link: {}\nTitle: {}\nAuthor: {}\nCreated: {}\nOptions:\n\t{}".format(link, data['title'],
                                                                                        author.display_name,
                                                                                        created_ago, fmt_options)
            await self.bot.say("```\n{}```".format(fmt))

    @strawpolls.command(name='create', aliases=['setup', 'add'], pass_context=True)
    @checks.customPermsOrRole(kick_members=True)
    async def create_strawpoll(self, ctx, title, *, options):
        """This command is used to setup a new strawpoll
        The format needs to be: poll create "title here" all options here
        Options need to be separated by using either one ` around each option
        Or use a code block (3 ` around the options), each option on it's own line"""
        match_single = getter.findall(options)
        match_multi = multi.findall(options)
        if match_single:
            options = match_single
            options = [option for option in options if option]
        elif match_multi:
            options = match_multi[0].splitlines()
            options = [option for option in options if option]
        else:
            await self.bot.say(
                "Please provide options for a new strawpoll! Use {}help if you do not know the format".format(
                    ctx.prefix))
            return
        payload = {'title': title,
                   'options': options}
        async with self.session.post(self.url, data=json.dumps(payload), headers=self.headers) as response:
            data = await response.json()

        all_polls = config.getContent('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}
        server_polls[data['id']] = {'author': ctx.message.author.id, 'date': str(pendulum.utcnow()), 'title': title}
        all_polls[ctx.message.server.id] = server_polls
        config.saveContent('strawpolls', all_polls)

        await self.bot.say("Link for your new strawpoll: https://strawpoll.me/{}".format(data['id']))

    @strawpolls.command(name='delete', aliases=['remove', 'stop'], pass_context=True)
    @checks.customPermsOrRole(kick_members=True)
    async def remove_strawpoll(self, ctx, poll_id: str = None):
        """This command can be used to delete one of the existing strawpolls
        If you don't provide an ID it will print the list of polls available"""

        all_polls = config.getContent('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}

        if poll_id:
            poll = server_polls.get(poll_id)
            if not poll:
                fmt = "\n".join("{}: {}".format(data['title'], _poll_id) for _poll_id, data in server_polls.items())
                await self.bot.say(
                    "There is no poll setup with that ID! Here is a list of the current polls```\n{}```".format(fmt))
            else:
                del server_polls[poll_id]
                all_polls[ctx.message.server.id] = server_polls
                config.saveContent('strawpolls', all_polls)
                await self.bot.say("I have just removed the poll with the ID {}".format(poll_id))
        else:
            fmt = "\n".join("{}: {}".format(data['title'], _poll_id) for _poll_id, data in server_polls.items())
            await self.bot.say("Here is a list of the polls on this server:\n```\n{}```".format(fmt))
