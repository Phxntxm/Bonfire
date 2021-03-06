import json
from discord.ext import commands
from utils import conjugator


class Japanese(commands.Cog):
    """A cog that provides some useful japanese tools"""

    def __init__(self):

        with open("utils/japanese_verbs.json") as f:
            verbs = json.load(f)

        for key, value in verbs.items():
            if value == 1:
                verbs[key] = conjugator.GodanVerbs(key)
            if value == 2:
                verbs[key] = conjugator.IchidanVerbs(key)
            if value == 3:
                verbs[key] = conjugator.IrregularVerbs(key)

        self.verbs = verbs

    @commands.command(aliases=["活用", "かつよう", "katsuyou"])
    async def conjugate(self, ctx, verb):
        """Conjugate the provided verb. Provide the verb in dictionary form

        EXAMPLE: !conjugate 食べる
        RESULT: A menu providing common conjugations for 食べる
        """
        verb = self.verbs.get(verb)

        if verb is None:
            return await ctx.send(f"Sorry, I don't know {verb}")

        await verb.display(ctx)


def setup(bot):
    bot.add_cog(Japanese())
