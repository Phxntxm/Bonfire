from discord.ext import commands
import discord

from . import utils

import asyncio


class Tags:
    """This class contains all the commands for custom tags"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def tags(self, ctx):
        """Prints all the custom tags that this server currently has

        EXAMPLE: !tags
        RESULT: All tags setup on this server"""
        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags')
        if tags:
            entries = [t['trigger'] for t in tags]
            pages = utils.Pages(self.bot, message=ctx.message, entries=entries)
            await pages.paginate()
        else:
            await ctx.send("There are no tags setup on this server!")

    @commands.command()
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def mytags(self, ctx):
        """Prints all the custom tags that this server that you own

        EXAMPLE: !mytags
        RESULT: All your tags setup on this server"""
        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags')
        if tags:
            entries = [t['trigger'] for t in tags if t['author'] == str(ctx.message.author.id)]
            if len(entries) == 0:
                await ctx.send("You have no tags setup on this server!")
            else:
                pages = utils.Pages(self.bot, message=ctx.message, entries=entries)
                await pages.paginate()
        else:
            await ctx.send("There are no tags setup on this server!")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
        The format to call a custom tag is !tag <tag>

        EXAMPLE: !tag butts
        RESULT: Whatever you setup for the butts tag!!"""
        tag = tag.lower().strip()
        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags')
        if tags:
            for t in tags:
                if t['trigger'].lower().strip() == tag:
                    await ctx.send("\u200B{}".format(t['result']))
                    return
            await ctx.send("There is no tag called {}".format(tag))
        else:
            await ctx.send("There are no tags setup on this server!")

    @tag.command(name='add', aliases=['create', 'setup'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
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

        trigger = msg.content.lower().strip()
        forbidden_tags = ['add', 'create', 'setup', 'edit', '']
        if len(trigger) > 100:
            await ctx.send("Please keep tag triggers under 100 characters")
            return
        elif trigger in forbidden_tags:
            await ctx.send(
                "Sorry, but your tag trigger was detected to be forbidden. "
                "Current forbidden tag triggers are: \n{}".format("\n".join(forbidden_tags)))
            return

        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags') or []
        if tags:
            for t in tags:
                if t['trigger'].lower().strip() == trigger:
                    await ctx.send("There is already a tag setup called {}!".format(trigger))
                    return

        try:
            await my_msg.delete()
            await msg.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        if trigger.lower() in ['edit', 'delete', 'remove', 'stop']:
            await ctx.send("You can't create a tag with {}!".format(trigger))
            return

        my_msg = await ctx.send(
            "Alright, your new tag can be called with {}!\n\nWhat do you want to be displayed with this tag?".format(
                trigger))

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send("You took too long!")
            return

        result = msg.content
        try:
            await my_msg.delete()
            await msg.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

        # The different DB settings
        tag = {
            'author': str(ctx.message.author.id),
            'trigger': trigger,
            'result': result
        }
        tags.append(tag)
        entry = {
            'server_id': str(ctx.message.guild.id),
            'tags': tags
        }
        self.bot.db.save('tags', entry)
        await ctx.send("I have just setup a new tag for this server! You can call your tag with {}".format(trigger))

    @tag.command(name='edit')
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def edit_tag(self, ctx, *, tag: str):
        """This will allow you to edit a tag that you have created
        EXAMPLE: !tag edit this tag
        RESULT: I'll ask what you want the new result to be"""
        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags')

        def check(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author and len(m.content) > 0

        if tags:
            for i, t in enumerate(tags):
                if t['trigger'] == tag:
                    if t['author'] == str(ctx.message.author.id):
                        my_msg = await ctx.send(
                            "Alright, what do you want the new result for the tag {} to be".format(tag))
                        try:
                            msg = await self.bot.wait_for("message", check=check, timeout=60)
                        except asyncio.TimeoutError:
                            await ctx.send("You took too long!")
                            return
                        new_tag = t.copy()
                        new_tag['result'] = msg.content
                        tags[i] = new_tag
                        try:
                            await my_msg.delete()
                            await msg.delete()
                        except discord.Forbidden:
                            pass
                        entry = {
                            'server_id': str(ctx.message.guild.id),
                            'tags': tags
                        }
                        self.bot.db.save('tags', entry)
                        await ctx.send("Alright, the tag {} has been updated".format(tag))
                        return
                    else:
                        await ctx.send("You can't edit someone else's tag!")
                        return
            await ctx.send("There isn't a tag called {}!".format(tag))
        else:
            await ctx.send("There are no tags setup on this server!")

    @tag.command(name='delete', aliases=['remove', 'stop'])
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    @utils.check_restricted()
    async def del_tag(self, ctx, *, tag: str):
        """Use this to remove a tag from use for this server
        Format to delete a tag is !tag delete <tag>

        EXAMPLE: !tag delete stupid_tag
        RESULT: Deletes that stupid tag"""
        tags = self.bot.db.load('tags', key=ctx.message.guild.id, pluck='tags')
        if tags:
            for t in tags:
                if t['trigger'].lower().strip() == tag:
                    if ctx.message.author.permissions_in(ctx.message.channel).manage_guild or str(
                            ctx.message.author.id) == t['author']:
                        tags.remove(t)
                        entry = {
                            'server_id': str(ctx.message.guild.id),
                            'tags': tags
                        }
                        self.bot.db.save('tags', entry)
                        await ctx.send("I have just removed the tag {}".format(tag))
                    else:
                        await ctx.send("You don't own that tag! You can't remove it!")
                    return
        else:
            await ctx.send("There are no tags setup on this server!")


def setup(bot):
    bot.add_cog(Tags(bot))
