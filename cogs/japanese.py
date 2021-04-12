import json
from discord.ext import commands
from utils import (
    conjugator,
    checks,
    request,
    Pages,
    CannotPaginate,
    chunks,
    FlashCardDisplay,
)


class Japanese(commands.Cog):
    """A cog that provides some useful japanese tools"""

    def __init__(self):

        # Load the verbs
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

        # Load the JLPT vocab
        with open("utils/japanese_vocabulary_n2.json") as f:
            n2 = json.load(f)
        self.n2_packs = list(chunks(n2, 50))
        with open("utils/japanese_vocabulary_n3.json") as f:
            n3 = json.load(f)
        self.n3_packs = list(chunks(n3, 50))
        with open("utils/japanese_vocabulary_n4.json") as f:
            n4 = json.load(f)
        self.n4_packs = list(chunks(n4, 50))
        with open("utils/japanese_vocabulary_n5.json") as f:
            n5 = json.load(f)
        self.n5_packs = list(chunks(n5, 50))

    @commands.command(aliases=["活用", "かつよう", "katsuyou"])
    @checks.can_run(send_messages=True)
    async def conjugate(self, ctx, verb):
        """Conjugate the provided verb. Provide the verb in dictionary form

        EXAMPLE: !conjugate 食べる
        RESULT: A menu providing common conjugations for 食べる
        """
        verb = self.verbs.get(verb)

        if verb is None:
            return await ctx.send(f"Sorry, I don't know {verb}")

        await verb.display(ctx)

    @commands.group(invoke_without_command=True)
    @checks.can_run(send_messages=True)
    async def anime(self, ctx):
        pass

    @anime.command(name="planning")
    @checks.can_run(send_messages=True)
    async def anime_planning(self, ctx, *, username):
        """Searches a user's planning list (ON ANILIST), and provides
        the top results based on the anime's average score

        EXAMPLE: !anime planning User!
        RESULT: Top results of User!'s planning list based on anime's average score
        """
        query = """
query ($name: String) {
  MediaListCollection(userName:$name, type:ANIME, status:PLANNING, sort:MEDIA_POPULARITY_DESC) {
    lists {
      status
      entries {
        media {
           title {
             english
             romaji
           }
          averageScore
          status
        }
      }
    }
  }
}
"""

        url = "https://graphql.anilist.co"
        payload = {"query": query, "variables": {"name": username}}

        response = await request(url, method="POST", json_data=payload)
        # Anilist API is broken and doesn't filter correctly, guess we have to do that ourselves
        data = []

        try:
            for x in response["data"]["MediaListCollection"]["lists"]:
                data.extend(
                    [
                        {
                            "title": r["media"]["title"]["english"]
                            if r["media"]["title"]["english"]
                            else r["media"]["title"]["romaji"],
                            "score": r["media"]["averageScore"],
                        }
                        for r in x["entries"]
                        if r["media"]["status"] == "FINISHED"
                    ]
                )
        except TypeError:
            return await ctx.send("Can't find an anilist with that username!")

        # Filtering done, sort it
        data = sorted(
            data,
            key=lambda n: n["score"],
            reverse=True,
        )
        # And convert to a string
        output = [f"**Score**: {x['score']} | **Title**: {x['title']}" for x in data]

        try:
            pages = Pages(ctx, entries=output, per_page=7)
            await pages.paginate()
        except CannotPaginate as e:
            await ctx.send(str(e))

    @commands.command()
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    @checks.can_run(send_messages=True)
    async def jlpt(self, ctx, level=None, pack: int = 0):
        """
        Runs a "flash card" pack for the JLPT level specified. This has N2-N5 available
        and there are 50 cards per pack, per level.

        EXAMPLE: !jlpt n5 1
        RESULT: Starts a flash card game of 50 cards from the JLPT n5 vocab list
        """
        if level not in ("n2", "n3", "n4", "n5"):
            return await ctx.send("JLPT level options are n2, n3, n4, or n5")
        packs = getattr(self, f"{level}_packs")
        if pack > len(packs) or pack < 1:
            return await ctx.send(f"The JLPT {level} has {len(packs)} available")

        pack = packs[pack - 1]
        await FlashCardDisplay(pack).start(ctx, wait=True)


def setup(bot):
    bot.add_cog(Japanese())
