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
        tags = config.get_content('tags') or {}
        # Simple generator that adds a tag to the list to print, if the tag is for this server
        fmt = "\n".join("{}".format(tag['tag']) for tag in tags if tag['server_id'] == ctx.message.server.id)
        await self.bot.say('```\n{}```'.format(fmt))

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
         The format to call a custom tag is !tag <tag>"""
        tags = config.get_content('tags') or {}
        # Same generator as the method for tags, other than the second check to see get the tag that is provided
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        if len(result) == 0:
            await self.bot.say('That tag does not exist!')
            return
        # We shouldn't ever have two tags of the same name, so just get the first result
        await self.bot.say("{}".format(result[0]['result']))

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

        tags = config.get_content('tags') or {}
        for t in tags:
            # Attempt to find a tag with that name, so that we update it instead of making a duplicate
            if t['tag'] == tag and t['server_id'] == ctx.message.server.id:
                t['result'] = tag_result
                await self.bot.say(
                    "I have just updated the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
                return
        # If we haven't found one, append a new one to the list
        tags.append({'server_id': ctx.message.server.id, 'tag': tag, 'result': tag_result})
        config.save_content('tags', tags)
        await self.bot.say(
            "I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))

    @tag.command(name='delete', aliases=['remove', 'stop'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag that from use for this server
        Format to delete a tag is !tag delete <tag>"""
        tags = config.get_content('tags') or {}
        # Get a list of the tags that match this server, and the name provided (should only ever be one if any)
        result = [t for t in tags if t['tag'] == tag and t['server_id'] == ctx.message.server.id]
        # If we haven't found one, can't delete it
        if len(result) == 0:
            await self.bot.say(
                "The tag {} does not exist! You can't remove something if it doesn't exist...".format(tag))
            return

        # Since there should never be more than one result due to our checks we've made, just remove the first result
        tags.remove(result[0])
        await self.bot.say('I have just removed the tag `{}`'.format(tag))
        config.save_content('tags', tags)


def setup(bot):
    bot.add_cog(Tags(bot))
