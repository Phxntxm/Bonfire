import json
from discord.ext import commands
from utils import conjugator, checks, request


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
        the top up to 10 results based on the anime's average score

        EXAMPLE: !anime planning User!
        RESULT: Top 10 results of User!'s planning list based on anime's average score
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

        for x in response["data"]["MediaListCollection"]["lists"]:
            data.extend(
                [
                    {
                        "title": r["media"]["title"]["english"],
                        "score": r["media"]["averageScore"],
                    }
                    for r in x["entries"]
                    if r["media"]["status"] == "FINISHED"
                ]
            )

        # Filtering done, sort it
        data = sorted(
            data,
            key=lambda n: n["score"],
            reverse=True,
        )
        # And convert to a string
        data = "\n".join(
            f"**Score**: {x['score']} | **Title**: {x['title']}" for x in data
        )

        await ctx.send(data)


def setup(bot):
    bot.add_cog(Japanese())
