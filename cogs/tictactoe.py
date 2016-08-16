from discord.ext import commands
import discord

from .utils import config
from .utils import checks

import re
import random


class Board:
    def __init__(self, player1, player2):
        self.board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]

        # Randomize who goes first when the board is created
        if random.SystemRandom().randint(0, 1):
            self.challengers = {'x': player1, 'o': player2}
        else:
            self.challengers = {'x': player2, 'o': player1}

        # X's always go first
        self.X_turn = True

    def full(self):
        for row in self.board:
            if ' ' in row:
                return False
        return True

    def can_play(self, player):
        if self.X_turn:
            return player == self.challengers['x']
        else:
            return player == self.challengers['o']

    def update(self, x, y):
        letter = 'x' if self.X_turn else 'o'
        if self.board[x][y] == ' ':
            self.board[x][y] = letter
        else:
            return False
        self.X_turn = not self.X_turn
        return True

    def check(self):
        # Checking all possiblities will be fun...
        # First base off the top-left corner, see if any possiblities with that match
        if self.board[0][0] == self.board[0][1] and self.board[0][0] == self.board[0][2] and self.board[0][0] != ' ':
            if self.board[0][0] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']
        if self.board[0][0] == self.board[1][0] and self.board[0][0] == self.board[2][0] and self.board[0][0] != ' ':
            if self.board[0][0] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']
        if self.board[0][0] == self.board[1][1] and self.board[0][0] == self.board[2][2] and self.board[0][0] != ' ':
            if self.board[0][0] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']

        # Next check the top-right corner, not re-checking the last possiblity that included it
        if self.board[0][2] == self.board[1][2] and self.board[0][2] == self.board[2][2] and self.board[0][2] != ' ':
            if self.board[0][2] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']
        if self.board[0][2] == self.board[1][1] and self.board[0][2] == self.board[2][0] and self.board[0][2] != ' ':
            if self.board[0][2] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']

        # Next up, bottom-right corner, only one possiblity to check here, other two have been checked
        if self.board[2][2] == self.board[2][1] and self.board[2][2] == self.board[2][0] and self.board[2][2] != ' ':
            if self.board[2][2] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']

        # No need to check the bottom-left, all posiblities have been checked now
        # Base things off the middle now, as we only need the two 'middle' possiblites that aren't diagonal
        if self.board[1][1] == self.board[0][1] and self.board[1][1] == self.board[2][1] and self.board[1][1] != ' ':
            if self.board[1][1] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']
        if self.board[1][1] == self.board[1][0] and self.board[1][1] == self.board[1][2] and self.board[1][1] != ' ':
            if self.board[1][1] == 'x':
                return self.challengers['x']
            else:
                return self.challengers['o']

        # Otherwise nothing has been found, return None
        return None

    def __str__(self):
        _board = " {}  |  {}  |  {}\n".format(self.board[0][0], self.board[0][1], self.board[0][2])
        _board += "———————————————\n"
        _board += " {}  |  {}  |  {}\n".format(self.board[1][0], self.board[1][1], self.board[1][2])
        _board += "———————————————\n"
        _board += " {}  |  {}  |  {}\n".format(self.board[2][0], self.board[2][1], self.board[2][2])
        return "```\n{}```".format(_board)


class TicTacToe:
    def __init__(self, bot):
        self.bot = bot
        self.boards = {}

    def create(self, server_id, player1, player2):
        self.boards[server_id] = Board(player1, player2)

        # Return whoever is x's so that we know who is going first
        return self.boards[server_id].challengers['x']

    def update_records(self, winner, loser):
        matches = config.get_content('tictactoe')
        if matches is None:
            matches = {winner.id: "1-0", loser.id: "0-1"}

        winner_stats = matches.get(winner.id) or {}
        winner_rating = winner_stats.get('rating') or 1000

        loser_stats = matches.get(loser.id) or {}
        loser_rating = loser_stats.get('rating') or 1000

        difference = abs(winner_rating - loser_rating)
        rating_change = 0
        count = 25
        while count <= difference:
            if count > 300:
                break
            rating_change += 1
            count += 25

        if winner_rating > loser_rating:
            winner_rating += 16 - rating_change
            loser_rating -= 16 - rating_change
        else:
            winner_rating += 16 + rating_change
            loser_rating -= 16 + rating_change

        winner_wins = winner_stats.get('wins') or 0
        winner_losses = winner_stats.get('losses') or 0
        loser_wins = loser_stats.get('wins') or 0
        loser_losses = loser_stats.get('losses') or 0
        winner_wins += 1
        loser_losses += 1

        winner_stats = {'wins': winner_wins, 'losses': winner_losses, 'rating': winner_rating}
        loser_stats = {'wins': loser_wins, 'losses': loser_losses, 'rating': loser_rating}
        matches[winner.id] = winner_stats
        matches[loser.id] = loser_stats

        return config.save_content('tictactoe', matches)

    @commands.group(pass_context=True, aliases=['tic', 'tac', 'toe'], no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def tictactoe(self, ctx, *, option: str):
        """Updates the current server's tic-tac-toe board
        You obviously need to be one of the players to use this
        It also needs to be your turn
        Provide top, left, bottom, right, middle as you want to mark where to play on the board"""
        player = ctx.message.author
        board = self.boards.get(ctx.message.server.id)
        if not board:
            await self.bot.say("There are currently no Tic-Tac-Toe games setup!")
            return
        if not board.can_play(player):
            await self.bot.say("You cannot play right now!")
            return

        # Search for the positions in the option given, the actual match doesn't matter, just need to check if it exists
        top = re.search('top', option)
        middle = re.search('middle', option)
        bottom = re.search('bottom', option)
        left = re.search('left', option)
        right = re.search('right', option)

        # Check if what was given was valid
        if top and bottom:
            await self.bot.say("That is not a valid location! Use some logic, come on!")
            return
        if left and right:
            await self.bot.say("That is not a valid location! Use some logic, come on!")
            return
        if not top and not bottom and not left and not right and not middle:
            await self.bot.say("Please provide a valid location to play!")
            return

        # Simple assignments
        if top:
            x = 0
        if bottom:
            x = 2
        if left:
            y = 0
        if right:
            y = 2
        if middle and not (top or bottom or left or right):
            x = 1
            y = 1
        if (top or bottom) and not (left or right):
            y = 1
        elif (left or right) and not (top or bottom):
            x = 1

        # If all checks have been made, x and y should now be defined correctly based on the matches, and we can go ahead and:
        if not board.update(x, y):
            await self.bot.say("Someone has already played there!")
            return
        winner = board.check()
        if winner:
            loser = board.challengers['x'] if board.challengers['x'] != winner else board.challengers['o']
            await self.bot.say("{} has won this game of TicTacToe, better luck next time {}".format(winner.display_name,
                                                                                                    loser.display_name))

            self.update_records(winner, loser)
            del self.boards[ctx.message.server.id]
        else:
            if board.full():
                await self.bot.say("This game has ended in a tie!")
                del self.boards[ctx.message.server.id]
            else:
                await self.bot.say(str(board))

    @tictactoe.command(name='start', aliases=['challenge', 'create'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def start_game(self, ctx, player2: discord.Member):
        """Starts a game of tictactoe with another player"""
        player1 = ctx.message.author
        if self.boards.get(ctx.message.server.id) is not None:
            await self.bot.say("Sorry but only one Tic-Tac-Toe game can be running per server!")
            return
        x_player = self.create(ctx.message.server.id, player1, player2)
        fmt = "A tictactoe game has just started between {} and {}".format(player1.display_name, player2.display_name)
        fmt += str(self.boards[ctx.message.server.id])
        fmt += "I have decided at random, and {} is going to be x's this game. It is your turn first!".format(
            x_player.display_name)
        await self.bot.say(fmt)


def setup(bot):
    bot.add_cog(TicTacToe(bot))
