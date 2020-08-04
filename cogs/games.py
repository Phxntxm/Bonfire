from discord.ext import commands

import utils


class Games(commands.Cog):

    @commands.guild_only()
    @utils.can_run(send_messages=True)
    @commands.command(aliases=["word_chain", "しりとり"])
    async def shiritori(self, ctx, *, start_word):
        """
        Starts a game of Shiritori, in which the last letter of the last word given
        has to be the first letter of the next word given. For example, if the word given is
        apple, then the next word can be elephant because apple ends in e and elephant begins in e

        The last player who entered a word cannot be the next person who enters a word
        The kana ん cannot be used, as no word in Japanese starts with this
        The word used cannot be a previously given word
        """
        def grab_letter(word, last=True):
            iterator = reversed(word) if last else iter(word)

            for char in iterator:
                if char.isalpha():
                    return char

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
            else:
                return True

        # Setup the info needed for the game
        message = ctx.message
        message.content = start_word
        words_used = []

        while True:
            # Grab the first letter of this new word and check it
            first_letter = grab_letter(message.content, last=False)
            # Include extra check for if this is the first word
            if words_used and first_letter != last_letter:
                break
            # Now set the "last" information, to start checking if it's correct
            last_word = message.content
            last_letter = grab_letter(last_word)
            last_author = message.author

            # Extra check for the japanese version, ん cannot be used
            if last_letter in ("ん", "ン"):
                break
            # Cannot reuuse words; though make sure this doesn't get caught on the very first usage
            if last_word in words_used and len(words_used) > 1:
                break

            # If we're here, then the last letter used was valid
            words_used.append(last_word)
            await message.add_reaction("✅")
            message = await ctx.bot.wait_for("message", check=check)

        # If we're here, game over, someone messed up
        await message.add_reaction("❌")
        if last_letter in ("ん", "ン"):
            await ctx.send(f"Wrong! ん cannot be used as the last kana!")
        else:
            await ctx.send(f"Wrong! {message.author.mention} is a loser!")


def setup(bot):
    bot.add_cog(Games())
