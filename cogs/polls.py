from discord.ext import commands
from . import utils

def to_keycap(c):
    return '\N{KEYCAP TEN}' if c == 10 else str(c) + '\u20e3'

class Poll:
    def __init__(self, message):
        self.message = message

    @property
    def guild(self):
        return self.message.guild

    @property
    def creator(self):
        return self.message.author

    @property
    def options(self):
        return self.message.reactions

    async def update_message(self):
        self.message = await self.message.channel.get_message(self.message.id)

    async def remove_other_reaction(self, reaction, member):
        """Ensures that this is the only reaction set for this user"""
        for r in self.options:
            if r.emoji == reaction.emoji:
                continue
            users = await r.users().flatten()
            if member.id in [x.id for x in users]:
                await self.message.remove_reaction(r, member)


class Polls:
    def __init__(self, bot):
        self.bot = bot
        self.polls = []

    async def create_poll(self, ctx, content):
        question, *options = content.split("\n")
        if len(options) == 0 or len(options) > 10:
            await ctx.send("Please provide between 1-10 options")
        else:
            fmt = "{} asked: {}\n".format(ctx.message.author.display_name, question)
            fmt += "\n".join(
                "{}: {}".format(to_keycap(i + 1), opt)
                for i, opt in enumerate(options)
            )

            msg = await ctx.send(fmt)
            for i, _ in enumerate(options):
                await msg.add_reaction(to_keycap(i + 1))
            p = Poll(msg)
            await p.update_message()
            self.polls.append(p)

    def get_poll(self, message):
        for p in self.polls:
            if p.message.id == message.id:
                return p

    async def on_reaction_add(self, reaction, user):
        if user.id == self.bot.user.id:
            return
        poll = self.get_poll(reaction.message)
        if poll:
            await poll.remove_other_reaction(reaction, user)


    @commands.command(pass_context=True)
    @commands.guild_only()
    @utils.custom_perms(send_messages=True)
    async def poll(self, ctx, *, question):
        """Sets up a poll based on the question that you have provided.
        Provide the question on the first line and the options on the following lines

        EXAMPLE: !poll This is my poll
        Option 1
        Option 2
        Option 3
        RESULT: A new poll people can vote on"""
        await self.create_poll(ctx, question)


def setup(bot):
    bot.add_cog(Polls(bot))
