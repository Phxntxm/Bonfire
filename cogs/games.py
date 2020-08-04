from discord.ext import commands

import utils


class Games(commands.Cog):

    @commands.guild_only()
    @utils.can_run(send_messages=True)
    @commands.command(aliases=["word_chain"])
    async def shiritori(self, ctx, *, start_word):
        """
        Starts a game of Shiritori, in which the last letter of the last word given
        has to be the first letter of the next word given. For example, if the word given is
        apple, then the next word can be elephant because apple ends in e and elephant begins in e

        The last player who entered a word cannot be the next person who enters a word
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

        # The info for the last word used
        last_word = start_word
        last_letter = grab_letter(start_word)
        last_author = ctx.author
        words_used = [start_word]

        # Add the reaction to the first message, to show we've started
        await ctx.message.add_reaction("✅")

        while True:
            message = await ctx.bot.wait_for("message", check=check)

            # Grab the first letter of this new word
            first_letter = grab_letter(message.content, last=False)

            if first_letter != last_letter:
                break

            # As long as we got a valid message, and the letter matches, then we're all good. Continue on
            last_word = message.content
            last_letter = grab_letter(message.content)
            last_author = message.author
            words_used.append(last_word)
            await message.add_reaction("✅")

        # If we're here, game over, someone messed up
        await message.add_reaction("❌")
        await ctx.send(f"Wrong! {message.author.mention} is a loser!")


def setup(bot):
    bot.add_cog(Games())
