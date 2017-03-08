import re

from discord.ext import commands

from . import utils


class Tags:
    """This class contains all the commands for custom tags"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def tags(self, ctx):
        """Prints all the custom tags that this server currently has

        EXAMPLE: !tags
        RESULT: All tags setup on this server"""
        tags = await utils.get_content('tags', {'server_id': ctx.message.guild.id})
        # Simple generator that adds a tag to the list to print, if the tag is for this server
        try:
            fmt = "\n".join("{}".format(tag['tag']) for tag in tags)
            await ctx.send('```\n{}```'.format(fmt))
        except TypeError:
            await ctx.send("There are not tags setup on this server!")

    @commands.group(invoke_without_command=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
         The format to call a custom tag is !tag <tag>

         EXAMPLE: !tag butts
         RESULT: Whatever you setup for the butts tag!!"""
        r_filter = lambda row: (row['server_id'] == ctx.message.guild.id) & (row['tag'] == tag)
        tags = await utils.filter_content('tags', r_filter)
        if tags is None:
            await ctx.send('That tag does not exist!')
            return
        # We shouldn't ever have two tags of the same name, so just get the first result
        await ctx.send("\u200B{}".format(tags[0]['result']))

    @tag.command(name='add', aliases=['create', 'start'], no_pm=True)
    @utils.custom_perms(kick_members=True)
    async def add_tag(self, ctx, *, result: str):
        """Use this to add a new tag that can be used in this server
        Format to add a tag is !tag add <tag> - <result>

        EXAMPLE: !tag add this is my new tag - This is what it will be
        RESULT: A tag that can be called by '!tag this is my new tag' and will output 'This is what it will be'"""
        try:
            # Use regex to get the matche for everything before and after a -
            match = re.search("(.*) - (.*)", result)
            tag = match.group(1).strip()
            tag_result = match.group(2).strip()
        # Next two checks are just to ensure there was a valid match found
        except AttributeError:
            await ctx.send(
                "Please provide the format for the tag in: {}tag add <tag> - <result>".format(ctx.prefix))
            return
        # If our regex failed to find the content (aka they provided the wrong format)
        if len(tag) == 0 or len(tag_result) == 0:
            await ctx.send(
                "Please provide the format for the tag in: {}tag add <tag> - <result>".format(ctx.prefix))
            return

        # Make sure the tag created does not mention everyone/here
        if '@everyone' in tag_result or '@here' in tag_result:
            await ctx.send("You cannot create a tag that mentions everyone!")
            return
        entry = {'server_id': ctx.message.guild.id, 'tag': tag, 'result': tag_result}
        r_filter = lambda row: (row['server_id'] == ctx.message.guild.id) & (row['tag'] == tag)
        # Try to create new entry first, if that fails (it already exists) then we update it
        if await utils.filter_content('tags', entry, r_filter):
            await ctx.send(
                "I have just added the tag `{0}`! You can call this tag by entering !tag {0}".format(tag))
        else:
            await ctx.send("That tag already exists!")

    @tag.command(name='delete', aliases=['remove', 'stop'], no_pm=True)
    @utils.custom_perms(kick_members=True)
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag from use for this server
        Format to delete a tag is !tag delete <tag>

        EXAMPLE: !tag delete stupid_tag
        RESULT: Deletes that stupid tag"""
        await ctx.send("Temporarily disabled")
        // TODO: Fix tags, this will inherently fix this method
        """r_filter = lambda row: (row['server_id'] == ctx.message.guild.id) & (row['tag'] == tag)
        if await utils.remove_content('tags', r_filter):
            await ctx.send('I have just removed the tag `{}`'.format(tag))
        else:
            await ctx.send(
                "The tag {} does not exist! You can't remove something if it doesn't exist...".format(tag))"""


def setup(bot):
    bot.add_cog(Tags(bot))
