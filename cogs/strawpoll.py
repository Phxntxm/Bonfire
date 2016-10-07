from discord.ext import commands
import discord

from .utils import config
from .utils import checks

import aiohttp
import re
import json
import pendulum
import rethinkdb as r


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

    @commands.group(aliases=['strawpoll', 'poll', 'polls'], pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def strawpolls(self, ctx, poll_id: str = None):
        """This command can be used to show a strawpoll setup on this server"""
        # Strawpolls cannot be 'deleted' so to handle whether a poll is running or not on a server
        # Just save the poll, which can then be removed when it should not be "running" anymore
        r_filter = {'server_id': ctx.message.server.id}
        polls = await config.get_content('strawpolls', r_filter)
        # Check if there are any polls setup on this server
        try:
            polls = polls[0]['polls']
        except TypeError:
            await self.bot.say("There are currently no strawpolls running on this server!")
            return
        # Print all polls on this server if poll_id was not provided
        if poll_id is None:
            fmt = "\n".join(
                "{}: https://strawpoll.me/{}".format(data['title'], data['poll_id']) for data in polls)
            await self.bot.say("```\n{}```".format(fmt))
        else:
            # Since strawpoll should never allow us to have more than one poll with the same ID
            # It's safe to assume there's only one result
            try:
                poll = [p for p in polls if p['poll_id'] == poll_id][0]
            except IndexError:
                await self.bot.say("That poll does not exist on this server!")
                return

            async with self.session.get("{}/{}".format(self.url, poll_id),
                                        headers={'User-Agent': 'Bonfire/1.0.0'}) as response:
                data = await response.json()

            # The response for votes and options is provided as two separate lists
            # We are enumarting the list of options, to print r (the option)
            # And the votes to match it, based on the index of the option
            # The rest is simple formatting
            fmt_options = "\n\t".join(
                "{}: {}".format(result, data['votes'][i]) for i, result in enumerate(data['options']))
            author = discord.utils.get(ctx.message.server.members, id=poll['author'])
            created_ago = (pendulum.utcnow() - pendulum.parse(poll['date'])).in_words()
            link = "https://strawpoll.me/{}".format(poll_id)
            fmt = "Link: {}\nTitle: {}\nAuthor: {}\nCreated: {} ago\nOptions:\n\t{}".format(link, data['title'],
                                                                                            author.display_name,
                                                                                            created_ago, fmt_options)
            await self.bot.say("```\n{}```".format(fmt))

    @strawpolls.command(name='create', aliases=['setup', 'add'], pass_context=True, no_pm=True)
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
        try:
            async with self.session.post(self.url, data=json.dumps(payload), headers=self.headers) as response:
                data = await response.json()
        except json.JSONDecodeError:
            await self.bot.say("Sorry, I couldn't connect to strawpoll at the moment. Please try again later")
            return

        # Save this strawpoll in the list of running strawpolls for a server
        poll_id = str(data['id'])

        r_filter = {'server_id': ctx.message.server.id}
        sub_entry = {'poll_id': poll_id,
                     'author': ctx.message.author.id,
                     'date': str(pendulum.utcnow()),
                     'title': title}

        entry = {'server_id': ctx.message.server.id,
                 'polls': [sub_entry]}
        update = {'polls': r.row['polls'].append(sub_entry)}
        if not await config.update_content('strawpolls', update, r_filter):
            await config.add_content('strawpolls', entry, {'poll_id': poll_id})
        await self.bot.say("Link for your new strawpoll: https://strawpoll.me/{}".format(poll_id))

    @strawpolls.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def remove_strawpoll(self, ctx, poll_id):
        """This command can be used to delete one of the existing strawpolls"""
        r_filter = {'server_id': ctx.message.server.id}
        content = await config.get_content('strawpolls', r_filter)
        try:
            content = content[0]['polls']
        except TypeError:
            await self.bot.say("There are no strawpolls setup on this server!")
            return

        polls = [poll for poll in content if poll['poll_id'] != poll_id]

        update = {'polls': polls}
        # Try to remove the poll based on the ID, if it doesn't exist, this will return false
        if await config.update_content('strawpolls', update, r_filter):
            await self.bot.say("I have just removed the poll with the ID {}".format(poll_id))
        else:
            await self.bot.say("There is no poll setup with that ID!")
