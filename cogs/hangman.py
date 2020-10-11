from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import discord

from utils import checks

import re
import asyncio


class Game:
    def __init__(self, word):
        self.word = word
        # This converts everything but spaces to a blank
        self.blanks = "".join(
            letter if not re.search("[a-zA-Z0-9]", letter) else "_" for letter in word
        )
        self.failed_letters = []
        self.guessed_letters = []
        self.fails = 0

    def guess_letter(self, letter):
        # No matter what, add this to guessed letters so we only have to do one check if a letter was already guessed
        self.guessed_letters.append(letter)
        if letter.lower() in self.word.lower():
            # Replace every occurence of the guessed letter, with the correct letter
            # Use the one in the word instead of letter, due to capitalization
            self.blanks = "".join(
                word_letter if letter.lower() == word_letter.lower() else self.blanks[i]
                for i, word_letter in enumerate(self.word)
            )
            return True
        else:
            self.fails += 1
            self.failed_letters.append(letter)
            return False

    def guess_word(self, word):
        if word.lower() == self.word.lower():
            self.blanks = self.word
            return True
        else:
            self.fails += 1
            return False

    def win(self):
        return self.word == self.blanks

    def failed(self):
        return self.fails == 7

    def __str__(self):
        # Here's our fancy formatting for the hangman picture
        # Each position in the hangman picture is either a space, or part of the man, based on how many fails there are
        man = "     ——\n"
        man += "    |  |\n"
        man += "    {}  |\n".format("o" if self.fails > 0 else " ")
        man += "   {}{}{} |\n".format(
            "/" if self.fails > 1 else " ",
            "|" if self.fails > 2 else " ",
            "\\" if self.fails > 3 else " ",
        )
        man += "    {}  |\n".format("|" if self.fails > 4 else " ")
        man += "   {} {} |\n".format(
            "/" if self.fails > 5 else " ", "\\" if self.fails > 6 else " "
        )
        man += "       |\n"
        man += "    ———————\n"
        fmt = "```\n{}```".format(man)
        # Then just add the guesses and the blanks to the string
        fmt += "```\nGuesses: {}\nWord: {}```".format(
            ", ".join(self.failed_letters), " ".join(self.blanks)
        )
        return fmt


class Hangman(commands.Cog):
    """Pretty self-explanatory"""

    games = {}
    pending_games = []

    def create(self, word, ctx):
        # Create a new game, then save it as the server's game
        game = Game(word)
        self.games[ctx.message.guild.id] = game
        game.author = ctx.message.author.id
        return game

    @commands.group(aliases=["hm"], invoke_without_command=True)
    @commands.guild_only()
    @commands.cooldown(1, 7, BucketType.user)
    @checks.can_run(send_messages=True)
    async def hangman(self, ctx, *, guess):
        """Makes a guess towards the server's currently running hangman game

        EXAMPLE: !hangman e (or) !hangman The Phrase!
        RESULT: Hopefully a win!"""
        game = self.games.get(ctx.message.guild.id)
        if not game:
            ctx.command.reset_cooldown(ctx)
            await ctx.send("There are currently no hangman games running!")
            return
        if game.author == ctx.message.author.id:
            await ctx.send("You cannot guess on your own hangman game!")
            return

        # Check if we are guessing a letter or a phrase. Only one letter can be guessed at a time
        # So if anything more than one was provided, we're guessing at the phrase
        # We're creating a fmt variable, so that we can  add a message for if a guess was correct or not
        # And also add a message for a loss/win
        if len(guess) == 1:
            if guess.lower() in game.guessed_letters:
                ctx.command.reset_cooldown(ctx)
                await ctx.send("That letter has already been guessed!")
                # Return here as we don't want to count this as a failure
                return
            if game.guess_letter(guess):
                fmt = "That's correct!"
            else:
                fmt = "Sorry, that letter is not in the phrase..."
        else:
            if game.guess_word(guess):
                fmt = "That's correct!"
            else:
                fmt = "Sorry that's not the correct phrase..."

        if game.win():
            fmt += " You guys got it! The phrase was `{}`".format(game.word)
            del self.games[ctx.message.guild.id]
        elif game.failed():
            fmt += " Sorry, you guys failed...the phrase was `{}`".format(game.word)
            del self.games[ctx.message.guild.id]
        else:
            fmt += str(game)

        await ctx.send(fmt)

    @hangman.command(name="create", aliases=["start"])
    @commands.guild_only()
    @checks.can_run(send_messages=True)
    async def create_hangman(self, ctx):
        """This is used to create a new hangman game
        A predefined phrase will be randomly chosen as the phrase to use

        EXAMPLE: !hangman start
        RESULT: This is pretty obvious .-."""

        # Only have one hangman game per server, since anyone
        # In a server (except the creator) can guess towards the current game
        if self.games.get(ctx.message.guild.id) is not None:
            await ctx.send("Sorry but only one Hangman game can be running per server!")
            return
        if ctx.guild.id in self.pending_games:
            await ctx.send(
                "Someone has already started one, and I'm now waiting for them..."
            )
            return

        try:
            msg = await ctx.message.author.send(
                "Please respond with a phrase you would like to use for your hangman game in **{}**\n\nPlease keep "
                "phrases less than 31 characters".format(ctx.message.guild.name)
            )
        except discord.Forbidden:
            await ctx.send(
                "I can't message you {}! Please allow DM's so I can message you and ask for the hangman phrase you "
                "want to use!".format(ctx.message.author.display_name)
            )
            return

        await ctx.send(
            "I have DM'd you {}, please respond there with the phrase you would like to setup".format(
                ctx.message.author.display_name
            )
        )

        def check(m):
            return m.channel == msg.channel and len(m.content) <= 30

        self.pending_games.append(ctx.guild.id)
        try:
            msg = await ctx.bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            self.pending_games.remove(ctx.guild.id)
            await ctx.send(
                "You took too long! Please look at your DM's as that's where I'm asking for the phrase you want to use"
            )
            return
        else:
            self.pending_games.remove(ctx.guild.id)

        forbidden_phrases = ["stop", "delete", "remove", "end", "create", "start"]
        if msg.content in forbidden_phrases:
            await ctx.send(
                "Detected forbidden hangman phrase; current forbidden phrases are: \n{}".format(
                    "\n".join(forbidden_phrases)
                )
            )
            return

        game = self.create(msg.content, ctx)
        # Let them know the game has started, then print the current game so that the blanks are shown
        await ctx.send(
            "Alright, a hangman game has just started, you can start guessing now!\n{}".format(
                str(game)
            )
        )

    @hangman.command(name="delete", aliases=["stop", "remove", "end"])
    @commands.guild_only()
    @checks.can_run(kick_members=True)
    async def stop_game(self, ctx):
        """Force stops a game of hangman
        This should realistically only be used in a situation like one player leaves
        Hopefully a moderator will not abuse it, but there's not much we can do to avoid that

        EXAMPLE: !hangman stop
        RESULT: No more men being hung"""
        if self.games.get(ctx.message.guild.id) is None:
            await ctx.send("There are no Hangman games running on this server!")
            return

        del self.games[ctx.message.guild.id]
        await ctx.send(
            "I have just stopped the game of Hangman, a new should be able to be started now!"
        )


def setup(bot):
    bot.add_cog(Hangman(bot))
