from discord.ext import commands

import collections
import utils


class Games(commands.Cog):
    def __init__(self):
        self.running_games = collections.defaultdict(dict)

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(aliases=["word_chain", "しりとり", "シリトリ"])
    @commands.max_concurrency(1, per=commands.BucketType.channel)
    async def shiritori(self, ctx, *, start_word):
        """
        Starts a game of Shiritori, in which the last letter of the last word given
        has to be the first letter of the next word given. For example, if the word given is
        apple, then the next word can be elephant because apple ends in e and elephant begins in e

        The last player who entered a word cannot be the next person who enters a word
        The kana ん cannot be used, as no word in Japanese starts with this
        The word used cannot be a previously given word
        """
        game = self.running_games["shiritori"].get(ctx.channel.id)

        def grab_letter(readings, last=True):
            readings = [reversed(word) if last else iter(word) for word in readings]

            letters = []

            for reading in readings:
                for char in reading:
                    if char.isalpha():
                        letters.append(char)

        def check(message):
            # Ensure it's in the same channel
            if message.channel != ctx.channel:
                return False
            # Ensure we aren't listening to a bot (like ourselves for example)
            elif message.author.bot:
                return False
            # The last person who gave a message cannot be the next one as well
            elif last_author is not None and message.author == last_author:
                return False
            # If no game is running then how did this even happen!?
            elif game is None:
                return False
            # If the author is not a player
            elif message.author not in game["players"]:
                return False
            # Otherwise we good
            else:
                return True

        # Setup the info needed for the game
        message = ctx.message
        message.content = start_word
        last_letters = None
        words_used = []

        # Ensure only one game is happening at once
        if game is not None:
            if ctx.author not in game["players"]:
                game["players"].append(ctx.author)
                await ctx.message.add_reaction("✅")
            else:
                await ctx.message.add_reaction("✅")
        else:
            self.running_games["shiritori"][ctx.channel.id] = {"players": []}

        await ctx.send(
            f"Shiritori game started! First word is `{start_word}`, any responses after this"
            "count towards the game"
        )

        while True:
            is_noun, readings = await utils.readings_for_word(message.content)
            # Only nouns can be used
            if not is_noun:
                break
            # Grab the first letter of this new word and check it
            first_letters = grab_letter(readings, last=False)
            # Include extra check for if this is the first word
            if words_used:
                # Check if there's a match between first and last letters
                if not any(char in first_letters for char in last_letters):
                    break
            # Now set the "last" information, to start checking if it's correct
            last_words = readings
            last_letters = grab_letter(last_words)
            last_author = message.author

            # Extra check for the japanese version, ん cannot be used
            if any(char in last_letters for char in ("ん", "ン")):
                break
            # Cannot reuuse words; though make sure this doesn't get caught on the very first usage
            if any(word in words_used for word in last_words) and len(words_used) >= 1:
                break

            # If we're here, then the last letter used was valid
            words_used.extend(last_words)
            await message.add_reaction("✅")
            message = await ctx.bot.wait_for("message", check=check)

        # If we're here, game over, someone messed up
        self.running_games["shiritori"][ctx.channel.id] = False
        await message.add_reaction("❌")
        if any(char in last_letters for char in ("ん", "ン")):
            await ctx.send("Wrong! ん cannot be used as the last kana!")
        else:
            await ctx.send(f"Wrong! {message.author.mention} is a loser!")


def setup(bot):
    bot.add_cog(Games())
