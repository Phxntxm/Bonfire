from discord.ext import commands
from .utils import config
from .utils import checks
import re


class Tags:
    """This class contains all the commands for custom tags"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def tags(self, ctx):
        """Prints all the custom tags that this server currently has"""
        tags = await config.get_content('tags', {'server_id': ctx.message.server.id})
        # Simple generator that adds a tag to the list to print, if the tag is for this server
        fmt = "\n".join("{}".format(tag['tag']) for tag in tags)
        await self.bot.say('```\n{}```'.format(fmt))

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
         The format to call a custom tag is !tag <tag>"""
        r_filter = lambda row: (row['server_id'] == ctx.message.server.id) & (row['tag'] == tag)
        tags = await config.get_content('tags', r_filter)
        if tags is None:
            await self.bot.say('That tag does not exist!')
            return
        # We shouldn't ever have two tags of the same name, so just get the first result
        await self.bot.say("\u200B{}".format(tags[0]['result']))

    @tag.command(name='add', aliases=['create', 'start'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def add_tag(self, ctx, *, result: str):
        """Use this to add a new tag that can be used in this server
        Format to add a tag is !tag add <tag> - <result>"""
        try:
            # Use regex to get the matche for everything before and after a -
            match = re.search("(.*) - (.*)", result)
            tag = match.group(1).strip()
            tag_result = match.group(2).strip()
        # Next two checks are just to ensure there was a valid match found
        except AttributeError:
            await self.bot.say(
                "Please provide the format for the tag in: {}tag add <tag> - <result>".format(ctx.prefix))
            return
        if len(tag) == 0 or len(tag_result) == 0:
            await self.bot.say(
                "Please provide the format for the tag in: {}tag add <tag> - <result>".format(ctx.prefix))
            return

        entry = {'server_id': ctx.message.server.id, 'tag': tag, 'result': tag_result}
        r_filter = lambda row: (row['server_id'] == ctx.message.server.id) & (row['tag'] == tag)
        # Try to create new entry first, if that fails (it already exists) then we update it
        if await config.add_content('tags', entry, r_filter):
            await self.bot.say(
                "I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
        else:
            await config.update_content('tags', entry, r_filter)
            await self.bot.say(
                "I have just updated the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))

    @tag.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag from use for this server
        Format to delete a tag is !tag delete <tag>"""
        r_filter = lambda row: (row['server_id'] == ctx.message.server.id) & (row['tag'] == tag)
        if await config.remove_content('tags', r_filter):
            await self.bot.say('I have just removed the tag `{}`'.format(tag))
        else:
            await self.bot.say(
                "The tag {} does not exist! You can't remove something if it doesn't exist...".format(tag))


def setup(bot):
    bot.add_cog(Tags(bot))
