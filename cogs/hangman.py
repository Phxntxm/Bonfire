from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import discord

from .utils import config
from .utils import checks

import re
import random

class Game:
    def __init__(self, word, creator):
        self.word = word
        self.creator = creator
        self.blanks = "".join(" " if letter == " " else "_" for letter in word)
        self.guessed_letters = []
        self.fails = 0
    
    def guess_letter(self, letter):
        if letter in self.word:
            self.blanks = "".join(letter if letter == word_letter else self.blanks[i] for i, word_letter in enumerate(self.word))
            return True
        else:
            self.fails += 1
            self.guessed_letters.append(letter)
            return False
    
    def guess_word(self, word):
        if word == self.word:
            return True
        else:
            self.fails += 1
            return False
    
    def win(self):
        return self.word == self.blanks
    
    def failed(self):
        return self.fails == 7
        
    
    def __str__(self):
        man = "     ——"
        man += "    |  |"
        man += "    {}  |".format("o" if fails > 0 else " ")
        man += "   {}{}{} |".format("/" if fails > 1 else " ", "|" if fails > 2 else " ", "\\" if fails > 3 else " ")
        man += "    {}  |".format("|" if fails > 4 else " ")
        man += "   {} {} |".format("/" if fails > 5 else " ", "\\" if fails > 6 else " ")
        man += "       |"
        man += "    ———————"
        fmt = "```\n{}```".format(man)
        fmt += "```\nGuesses: {}\nWord: {}```".format(", ".join(guessed_letters), " ".join(self.blanks))
        return fmt
    
class Hangman:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}
    
    def create(self, word, ctx):
        game = Game(word, ctx.message.author)
        self.games[ctx.message.server.id] = game
        return game
        
    
    @commands.group(aliases=['hm'], pass_context=True, no_pm=True, invoke_without_command=True)
    @commands.cooldown(1, 30, BucketType.user)
    @checks.customPermsOrRole(send_messages=True)
    async def hangman(self, ctx, *, guess):
        """Makes a guess towards the server's currently running hangman game"""
        game = self.games.get(ctx.message.server.id)
        if not game:
            await self.bot.say("There are currently no hangman games running!")
            return
        if ctx.message.author == game.creator:
            await self.bot.say("You can't guess at your own hangman gam! :S")
            return
            
        if len(guess) == 1:
            if game.guess_letter(guess):
                fmt = "That's correct!"
            else:
                fmt = "Sorry, that letter is not in the phrase..."
        else:
            if game.guess_word(guess):
                fmt = "That's correct!"
            else:
                fmt = "Sorry that's not the correct phrase..."
        
        if game.win:
            fmt += " You guys got it! The word was `{}`".format(game.word)
            del server.games[ctx.message.server.id]
        elif game.failed:
            fmt += " Sorry, you guys failed...the word was `{}`".format(game.word)
            del server.games[ctx.message.server.id]
        else:
            fmt += str(game)
        
        await self.bot.say(fmt)
    
    @hangman.command(name='create', aliases=['start'], no_pm=True, pass_context=True)
    @checks.customPermsOrRole(send_messages=True)
    async def create_hangman(self, ctx):
        """This is used to create a new hangman game
        Due to the fact that I might not be able to delete a message, I will PM you and ask for the phrase you want.
        The phrase needs to be under 30 characters"""
        
        if self.games.get(ctx.message.server.id) != None:
            await self.bot.say("Sorry but only one Hangman game can be running per server!")
            return
            
        check = lambda m: len(m.content) < 30
        
        # Doing this so that while we wait for the phrase, another one cannot be started.
        self.games[ctx.message.server.id] = "placeholder"
        
        await self.bot.say("I have just PM'd you {}, please respond there with the phrase you want to start a new hangman game with")
        _msg = await self.bot.whisper("Please respond with the phrase you would like to use for your new hangman game\n"
                                        "Please note that it must be under 30 characters long")
        msg = await self.bot.wait_for_message(timeout=60.0, channel=_msg.channel, check=check)
        
        if not msg:
            await self.bot.whisper("Sorry, you took too long.")
            del self.games[ctx.message.server.id]
            return
        else:
            game = self.create(msg.content, ctx)
        await self.bot.say("Alright, a hangman game has just started, you can start guessing now!\n{}".format(str(game)))

def setup(bot):
    bot.add_cog(Hangman(bot))
