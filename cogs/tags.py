from discord.ext import commands
import discord

import utils

import asyncio


class Tags:
    """This class contains all the commands for custom tags"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def tags(self, ctx):
        """Prints all the custom tags that this server currently has

        EXAMPLE: !tags
        RESULT: All tags setup on this server"""
        tags = await self.bot.db.fetch("SELECT trigger FROM tags WHERE guild=$1", ctx.guild.id)

        if len(tags) > 0:
            entries = [t['trigger'] for t in tags]
            pages = utils.Pages(ctx, entries=entries)
            await pages.paginate()
        else:
            await ctx.send("There are no tags setup on this server!")

    @commands.command()
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def mytags(self, ctx):
        """Prints all the custom tags that this server that you own

        EXAMPLE: !mytags
        RESULT: All your tags setup on this server"""
        tags = await self.bot.db.fetch(
            "SELECT trigger FROM tags WHERE guild=$1 AND creator=$2",
            ctx.guild.id,
            ctx.author.id
        )

        if len(tags) > 0:
            entries = [t['trigger'] for t in tags]
            pages = utils.Pages(ctx, entries=entries)
            await pages.paginate()
        else:
            await ctx.send("You have no tags on this server!")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def tag(self, ctx, *, tag: str):
        """This can be used to call custom tags
        The format to call a custom tag is !tag <tag>

        EXAMPLE: !tag butts
        RESULT: Whatever you setup for the butts tag!!"""
        tag = await self.bot.db.fetchrow(
            "SELECT id, result FROM tags WHERE guild=$1 AND trigger=$2",
            ctx.guild.id,
            tag.lower().strip()
        )

        if tag:
            await ctx.send("\u200B{}".format(tag['result']))
            await self.bot.db.execute("UPDATE tags SET uses = uses + 1 WHERE id = $1", tag['id'])
        else:
            await ctx.send("There is no tag called {}".format(tag))

    @tag.command(name='add', aliases=['create', 'setup'])
    @commands.guild_only()
    @utils.can_run(send_messages=True)
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
        forbidden_tags = ['add', 'create', 'setup', 'edit', 'info', 'delete', 'remove', 'stop']
        if len(trigger) > 100:
            await ctx.send("Please keep tag triggers under 100 characters")
            return
        elif trigger.lower() in forbidden_tags:
            await ctx.send(
                "Sorry, but your tag trigger was detected to be forbidden. "
                "Current forbidden tag triggers are: \n{}".format("\n".join(forbidden_tags)))
            return

        tag = await self.bot.db.fetchrow(
            "SELECT result FROM tags WHERE guild=$1 AND trigger=$2",
            ctx.guild.id,
            trigger.lower().strip()
        )
        if tag:
            await ctx.send("There is already a tag setup called {}!".format(trigger))
            return

        try:
            await my_msg.delete()
            await msg.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

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

        await ctx.send("I have just setup a new tag for this server! You can call your tag with {}".format(trigger))
        await self.bot.db.execute(
            "INSERT INTO tags(guild, creator, trigger, result) VALUES ($1, $2, $3, $4)",
            ctx.guild.id,
            ctx.author.id,
            trigger,
            result
        )

    @tag.command(name='edit')
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def edit_tag(self, ctx, *, trigger: str):
        """This will allow you to edit a tag that you have created
        EXAMPLE: !tag edit this tag
        RESULT: I'll ask what you want the new result to be"""
        def check(m):
            return m.channel == ctx.message.channel and m.author == ctx.message.author and len(m.content) > 0

        tag = await self.bot.db.fetchrow(
            "SELECT id, trigger FROM tags WHERE guild=$1 AND creator=$2 AND trigger=$3",
            ctx.guild.id,
            ctx.author.id,
            trigger
        )

        if tag:
            my_msg = await ctx.send(f"Alright, what do you want the new result for the tag {tag} to be")
            try:
                msg = await self.bot.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send("You took too long!")
                return

            new_result = msg.content

            try:
                await my_msg.delete()
                await msg.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass

            await ctx.send(f"Alright, the tag {trigger} has been updated")
            await self.bot.db.execute("UPDATE tags SET result=$1 WHERE id=$2", new_result, tag['id'])
        else:
            await ctx.send(f"You do not have a tag called {trigger} on this server!")

    @tag.command(name='delete', aliases=['remove', 'stop'])
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def del_tag(self, ctx, *, trigger: str):
        """Use this to remove a tag from use for this server
        Format to delete a tag is !tag delete <tag>

        EXAMPLE: !tag delete stupid_tag
        RESULT: Deletes that stupid tag"""

        tag = await self.bot.db.fetchrow(
            "SELECT id FROM tags WHERE guild=$1 AND creator=$2 AND trigger=$3",
            ctx.guild.id,
            ctx.author.id,
            trigger
        )

        if tag:
            await ctx.send(f"I have just deleted the tag {trigger}")
            await self.bot.db.execute("DELETE FROM tags WHERE id=$1", tag['id'])
        else:
            await ctx.send(f"You do not own a tag called {trigger} on this server!")

    @tag.command(name="info")
    @commands.guild_only()
    @utils.can_run(send_messages=True)
    async def info_tag(self, ctx, *, trigger: str):
        """Shows some information a bout the tag given"""

        tag = await self.bot.db.fetchrow(
            "SELECT creator, uses, trigger FROM tags WHERE guild=$1 AND trigger=$2",
            ctx.guild.id,
            trigger
        )

        embed = discord.Embed(title=tag['trigger'])
        creator = ctx.guild.get_member(tag['creator'])
        if creator:
            embed.set_author(name=creator.display_name, url=creator.avatar_url)
        embed.add_field(name="Uses", value=tag['uses'])
        embed.add_field(name="Owner", value=creator.mention)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Tags(bot))
