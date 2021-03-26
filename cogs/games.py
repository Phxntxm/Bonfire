from discord.ext import commands

import collections
import utils


class Games(commands.Cog):
    def __init__(self):
        self.running_games = collections.defaultdict(dict)

    @commands.command(aliases=["word_chain", "しりとり", "シリトリ"])
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def shiritori(self, ctx, *, word):
        """
        Starts or play on a game of Shiritori, in which the last letter of the last word given
        has to be the first letter of the next word given. For example, if the word given is
        apple, then the next word can be elephant because apple ends in e and elephant begins in e

        The last player who entered a word cannot be the next person who enters a word
        The kana ん cannot be used, as no word in Japanese starts with this
        The word used cannot be a previously given word
        """
        game = self.running_games["shiritori"].get(ctx.channel.id)
        # Ensure only one game is happening at once
        if game is not None:
            if ctx.author not in game["players"]:
                game["players"].append(ctx.author)
        else:
            self.running_games["shiritori"][ctx.channel.id] = {
                "players": [ctx.author],
                "words_used": [],
                "last_letters": [],
                "last_author": ctx.author,
            }
            game = self.running_games["shiritori"].get(ctx.channel.id)

        def grab_letter(readings, last=True):
            readings = [reversed(word) if last else iter(word) for word in readings]

            letters = []

            for reading in readings:
                for char in reading:
                    if char.isalpha():
                        letters.append(char)
                        break

            return letters

        # Don't allow last author to guess again
        if game["words_used"] and ctx.author == game["last_author"]:
            return await ctx.send("You guessed last, someone else's turn")
        is_noun, readings = await utils.readings_for_word(word)
        # Only nouns can be used
        if not is_noun:
            self.running_games["shiritori"][ctx.channel.id] = None
            return await ctx.send(
                f"Game over! {ctx.author} loses, only nouns can be used"
            )
        # Grab the first letter of this new word and check it
        first_letters = grab_letter(readings, last=False)
        last_letters = grab_letter(readings, last=False)
        # Include extra check for if this is the first word
        if game["words_used"]:
            # Check if there's a match between first and last letters
            if not any(char in first_letters for char in game["last_letters"]):
                self.running_games["shiritori"][ctx.channel.id] = None
                return await ctx.send(
                    f"Game over! {ctx.author} loses, first letter of {word} did not match last letter used"
                )

        # ん cannot be used
        if any(char in last_letters for char in ("ん", "ン")):
            self.running_games["shiritori"][ctx.channel.id] = None
            return await ctx.send(
                f"Game over! {ctx.author} loses, last letter cannot be ん"
            )
        # Cannot reuuse words
        if word in game["words_used"]:
            self.running_games["shiritori"][ctx.channel.id] = None
            return await ctx.send(
                f"Game over! {ctx.author} loses, {word} has already been used"
            )

        # If we're here, then the last letter used was valid, save stuff
        game["words_used"].append(word)
        game["last_letters"] = last_letters
        game["last_author"] = ctx.author
        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Games())
