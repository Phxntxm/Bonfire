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
        # In this class we'll only be sending POST requests when creating a poll
        # Strawpoll requires the content-type, so just add that to the default headers
        self.headers = {'User-Agent': 'Bonfire/1.0.0',
                        'Content-Type': 'application/json'}
        self.session = aiohttp.ClientSession()

    @commands.group(aliases=['strawpoll', 'poll', 'polls'], pass_context=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def strawpolls(self, ctx, poll_id: str = None):
        """This command can be used to show a strawpoll setup on this server"""
        # Strawpolls cannot be 'deleted' so to handle whether a poll is running or not on a server
        # Just save the poll in the config file, which can then be removed when it should not be "running" anymore
        all_polls = config.get_content('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}
        if not server_polls:
            await self.bot.say("There are currently no strawpolls running on this server!")
            return
        # If no poll_id was provided, print a list of all current running poll's on this server
        if not poll_id:
            fmt = "\n".join(
                "{}: https://strawpoll.me/{}".format(data['title'], _id) for _id, data in server_polls.items())
            await self.bot.say("```\n{}```".format(fmt))
        # Else if a valid poll_id was provided, print info about that poll
        elif poll_id in server_polls.keys():
            poll = server_polls[poll_id]

            async with self.session.get("{}/{}".format(self.url, poll_id),
                                        headers={'User-Agent': 'Bonfire/1.0.0'}) as response:
                data = await response.json()

            # The response for votes and options is provided as two separate lists
            # We are enumarting the list of options, to print r (the option)
            # And the votes to match it, based on the index of the option
            # The rest is simple formatting
            fmt_options = "\n\t".join(
                "{}: {}".format(r, data['votes'][i]) for i, r in enumerate(data['options']))
            author = discord.utils.get(ctx.message.server.members, id=poll['author'])
            created_ago = (pendulum.utcnow() - pendulum.parse(poll['date'])).in_words()
            link = "https://strawpoll.me/{}".format(poll_id)
            fmt = "Link: {}\nTitle: {}\nAuthor: {}\nCreated: {} ago\nOptions:\n\t{}".format(link, data['title'],
                                                                                            author.display_name,
                                                                                            created_ago, fmt_options)
            await self.bot.say("```\n{}```".format(fmt))

    @strawpolls.command(name='create', aliases=['setup', 'add'], pass_context=True)
    @checks.custom_perms(kick_members=True)
    async def create_strawpoll(self, ctx, title, *, options):
        """This command is used to setup a new strawpoll
        The format needs to be: poll create "title here" all options here
        Options need to be separated by using either one ` around each option
        Or use a code block (3 ` around the options), each option on it's own line"""
        # The following should use regex to search for the options inside of the two types of code blocks with `
        # We're using this instead of other things, to allow most used puncation inside the options
        match_single = getter.findall(options)
        match_multi = multi.findall(options)
        # Since match_single is already going to be a list, we just set
        # The options to match_single and remove any blank entries
        if match_single:
            options = match_single
            options = [option for option in options if option]
        # Otherwise, options need to be set based on the list, split by lines.
        # Then remove blank entries like the last one
        elif match_multi:
            options = match_multi[0].splitlines()
            options = [option for option in options if option]
        # If neither is found, then error out and let them know to use the help command, since this one is a bit finicky
        else:
            await self.bot.say(
                "Please provide options for a new strawpoll! Use {}help {} if you do not know the format".format(
                    ctx.prefix, ctx.command.qualified_name))
            return
        # Make the post request to strawpoll, creating the poll, and returning the ID
        # The ID is all we really need from the returned data, as the rest we already sent/are not going to use ever
        payload = {'title': title,
                   'options': options}
        async with self.session.post(self.url, data=json.dumps(payload), headers=self.headers) as response:
            data = await response.json()

        # Save this strawpoll in the list of running strawpolls for a server
        all_polls = config.get_content('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}
        server_polls[data['id']] = {'author': ctx.message.author.id, 'date': str(pendulum.utcnow()), 'title': title}
        all_polls[ctx.message.server.id] = server_polls
        config.save_content('strawpolls', all_polls)

        await self.bot.say("Link for your new strawpoll: https://strawpoll.me/{}".format(data['id']))

    @strawpolls.command(name='delete', aliases=['remove', 'stop'], pass_context=True)
    @checks.custom_perms(kick_members=True)
    async def remove_strawpoll(self, ctx, poll_id: str = None):
        """This command can be used to delete one of the existing strawpolls
        If you don't provide an ID it will print the list of polls available"""

        all_polls = config.get_content('strawpolls') or {}
        server_polls = all_polls.get(ctx.message.server.id) or {}

        # Check if a poll_id was provided, if it is then we can continue, if not print the list of current polls
        if poll_id:
            poll = server_polls.get(poll_id)
            # Check if no poll exists with that ID, then print a list of the polls
            if not poll:
                fmt = "\n".join("{}: {}".format(data['title'], _poll_id) for _poll_id, data in server_polls.items())
                await self.bot.say(
                    "There is no poll setup with that ID! Here is a list of the current polls```\n{}```".format(fmt))
            else:
                # Delete the poll that was just found
                del server_polls[poll_id]
                all_polls[ctx.message.server.id] = server_polls
                config.save_content('strawpolls', all_polls)
                await self.bot.say("I have just removed the poll with the ID {}".format(poll_id))
        else:
            fmt = "\n".join("{}: {}".format(data['title'], _poll_id) for _poll_id, data in server_polls.items())
            await self.bot.say("Here is a list of the polls on this server:\n```\n{}```".format(fmt))
