from discord.ext import commands
import discord

from . import utils

import asyncio
import rethinkdb as r

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
        tags = await utils.get_content('tags', str(ctx.message.guild.id))
        if tags:
            entries = [t['trigger'] for t in tags['tags']]
            pages = utils.Pages(self.bot, message=ctx.message, entries=entries)
            await pages.paginate()
        else:
            await ctx.send("There are no tags setup on this server!")

    @commands.group(invoke_without_command=True, no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
        The format to call a custom tag is !tag <tag>

        EXAMPLE: !tag butts
        RESULT: Whatever you setup for the butts tag!!"""
        tags = await utils.get_content('tags', str(ctx.message.guild.id))
        if tags:
            for t in tags['tags']:
                if t['trigger'] == tag:
                    await ctx.send(t['result'])
                    return
            await ctx.send("There is no tag called {}".format(tag))
        else:
            await ctx.send("There are no tags setup on this server!")


    @tag.command(name='add', aliases=['create', 'setup'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def add_tag(self, ctx):
        """Use this to add a new tag that can be used in this server

        EXAMPLE: !tag add
        RESULT: A follow-along in order to create a new tag"""
        def check(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author and len(m.content) > 0
        my_msg = await ctx.send("Ready to setup a new tag! What do you want the trigger for the tag to be?")

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("You took too long!")
            return

        trigger = msg.content
        try:
            await my_msg.delete()
            await msg.delete()
        except discord.Forbidden:
            pass

        my_msg = await ctx.send("Alright, your new tag can be called with {}!\n\nWhat do you want to be displayed with this tag?".format(trigger))

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("You took too long!")
            return

        result = msg.content
        try:
            await my_msg.delete()
            await msg.delete()
        except discord.Forbidden:
            pass

        # The different DB settings
        tag = {
            'author': str(ctx.message.author.id),
            'trigger': trigger,
            'result': result
        }
        entry = {
            'server_id': str(ctx.message.guild.id),
            'tags': [tag]
        }
        key = str(ctx.message.guild.id)
        if not await utils.add_content('tags', entry):
            await utils.update_content('tags', {'tags': r.row['tags'].append(tag)}, key)
        await ctx.send("I have just setup a new tag for this server! You can call your tag with {}".format(trigger))


    @tag.command(name='delete', aliases=['remove', 'stop'], no_pm=True)
    @utils.custom_perms(send_messages=True)
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag from use for this server
        Format to delete a tag is !tag delete <tag>

        EXAMPLE: !tag delete stupid_tag
        RESULT: Deletes that stupid tag"""
        key = str(ctx.message.guild.id)
        tags = await utils.get_content('tags', key)
        if tags:
            for t in tags['tags']:
                if t['trigger'] == tag:
                    if ctx.message.author.permissions_in(ctx.message.channel).manage_guild or str(ctx.message.author.id) == t['author']:
                        tags['tags'].remove(t)
                        await utils.update_content('tags', tags, key)
                        await ctx.send("I have just removed the tag {}".format(tag))
                    else:
                        await ctx.send("You don't own that tag! You can't remove it!")
                    return
        else:
            await ctx.send("There are no tags setup on this server!")


def setup(bot):
    bot.add_cog(Tags(bot))
