from discord.ext import commands
import discord

from .utils import config
from .utils import checks

import re
import random


class Board:
    def __init__(self, player1, player2):
        # Our board just needs to be a 3x3 grid. To keep formatting nice, each one is going to be a space to start
        self.board = [[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]

        # Randomize who goes first when the board is created
        if random.SystemRandom().randint(0, 1):
            self.challengers = {'x': player1, 'o': player2}
        else:
            self.challengers = {'x': player2, 'o': player1}

        # X's always go first
        self.X_turn = True

    def full(self):
        # For this check we just need to see if there is a space anywhere, if there is then we're not full
        for row in self.board:
            if ' ' in row:
                return False
        return True

    def can_play(self, player):
        # Simple check to see if the player is the one that's up
        if self.X_turn:
            return player == self.challengers['x']
        else:
            return player == self.challengers['o']

    def update(self, x, y):
        # If it's x's turn, we place an x, otherwise place an o
        letter = 'x' if self.X_turn else 'o'
        # Make sure the place we're trying to update is blank, we can't override something
        if self.board[x][y] == ' ':
            self.board[x][y] = letter
        else:
            return False
        # If we were succesful in placing the piece, we need to switch whose turn it is
        self.X_turn = not self.X_turn
        return True

    def check(self):
        # Checking all possiblities will be fun...
        # First base off the top-left corner, see if any possiblities with that match
        # We need to also make sure that the place is not blank, so that 3 in a row that are blank doesn't cause a 'win'
        # Top-left, top-middle, top right
        if self.board[0][0] == self.board[0][1] and self.board[0][0] == self.board[0][2] and self.board[0][0] != ' ':
            return self.challengers[self.board[0][0]]
        # Top-left, middle-left, bottom-left
        if self.board[0][0] == self.board[1][0] and self.board[0][0] == self.board[2][0] and self.board[0][0] != ' ':
            return self.challengers[self.board[0][0]]
        # Top-left, middle, bottom-right
        if self.board[0][0] == self.board[1][1] and self.board[0][0] == self.board[2][2] and self.board[0][0] != ' ':
            return self.challengers[self.board[0][0]]

        # Next check the top-right corner, not re-checking the last possiblity that included it
        # Top-right, middle-right, bottom-right
        if self.board[0][2] == self.board[1][2] and self.board[0][2] == self.board[2][2] and self.board[0][2] != ' ':
            return self.challengers[self.board[0][2]]
        # Top-right, middle, bottom-left
        if self.board[0][2] == self.board[1][1] and self.board[0][2] == self.board[2][0] and self.board[0][2] != ' ':
            return self.challengers[self.board[0][2]]

        # Next up, bottom-right corner, only one possiblity to check here, other two have been checked
        # Bottom-right, bottom-middle, bottom-left
        if self.board[2][2] == self.board[2][1] and self.board[2][2] == self.board[2][0] and self.board[2][2] != ' ':
            return self.challengers[self.board[2][2]]

        # No need to check the bottom-left, all posiblities have been checked now
        # Base things off the middle now, as we only need the two 'middle' possiblites that aren't diagonal
        # Top-middle, middle, bottom-middle
        if self.board[1][1] == self.board[0][1] and self.board[1][1] == self.board[2][1] and self.board[1][1] != ' ':
            return self.challengers[self.board[1][1]]
        # Left-middle, middle, right-middle
        if self.board[1][1] == self.board[1][0] and self.board[1][1] == self.board[1][2] and self.board[1][1] != ' ':
            return self.challengers[self.board[1][1]]

        # Otherwise nothing has been found, return None
        return None

    def __str__(self):
        # Simple formatting here when you look at it, enough spaces to even out where everything is
        # Place whatever is at the grid in place, whether it's x, o, or blank
        _board = " {}  |  {}  |  {}\n".format(self.board[0][0], self.board[0][1], self.board[0][2])
        _board += "———————————————\n"
        _board += " {}  |  {}  |  {}\n".format(self.board[1][0], self.board[1][1], self.board[1][2])
        _board += "———————————————\n"
        _board += " {}  |  {}  |  {}\n".format(self.board[2][0], self.board[2][1], self.board[2][2])
        return "```\n{}```".format(_board)


def update_records(winner, loser):
    # This is the exact same formula as the battling update.
    # The only difference is I use the word "match" instead of "battle"
    matches = config.get_content('tictactoe') or {}

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


class TicTacToe:
    def __init__(self, bot):
        self.bot = bot
        self.boards = {}

    def create(self, server_id, player1, player2):
        self.boards[server_id] = Board(player1, player2)

        # Return whoever is x's so that we know who is going first
        return self.boards[server_id].challengers['x']

    @commands.command(pass_context=True, no_pm=True, name='test')
    @checks.custom_perms(send_messages=True)
    async def test_sharding(self, ctx):
        await self.bot.say("Responded on shard {}\nboard is {}".format(config.shard_id, self.boards.get(ctx.message.server.id)))

    @commands.group(pass_context=True, aliases=['tic', 'tac', 'toe'], no_pm=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def tictactoe(self, ctx, *, option: str):
        """Updates the current server's tic-tac-toe board
        You obviously need to be one of the players to use this
        It also needs to be your turn
        Provide top, left, bottom, right, middle as you want to mark where to play on the board"""
        player = ctx.message.author
        board = self.boards.get(ctx.message.server.id)
        # Need to make sure the board exists before allowing someone to play
        if not board:
            await self.bot.say("There are currently no Tic-Tac-Toe games setup!")
            return
        # Now just make sure the person can play, this will fail if o's are up and x tries to play
        # Or if someone else entirely tries to play
        if not board.can_play(player):
            await self.bot.say("You cannot play right now!")
            return

        # Search for the positions in the option given, the actual match doesn't matter, just need to check if it exists
        top = re.search('top', option)
        middle = re.search('middle', option)
        bottom = re.search('bottom', option)
        left = re.search('left', option)
        right = re.search('right', option)

        # Just a bit of logic to ensure nothing that doesn't make sense is given
        if top and bottom:
            await self.bot.say("That is not a valid location! Use some logic, come on!")
            return
        if left and right:
            await self.bot.say("That is not a valid location! Use some logic, come on!")
            return
        # Make sure at least something was given
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
        # If middle was given and nothing else, we need the exact middle
        if middle and not (top or bottom or left or right):
            x = 1
            y = 1
        # If just top or bottom was given, we assume this means top-middle or bottom-middle
        # We don't need to do anything fancy with top/bottom as it's already assigned, just assign middle
        if (top or bottom) and not (left or right):
            y = 1
        # If just left or right was given, we assume this means left-middle or right-middle
        # We don't need to do anything fancy with left/right as it's already assigned, just assign middle
        elif (left or right) and not (top or bottom):
            x = 1

        # If all checks have been made, x and y should now be defined
        # Correctly based on the matches, and we can go ahead and update the board
        # We've already checked if the author can play, so there's no need to make any additional checks here
        # board.update will handle which letter is placed
        # If it returns false however, then someone has already played in that spot and nothing was updated
        if not board.update(x, y):
            await self.bot.say("Someone has already played there!")
            return
        # Next check if there's a winner
        winner = board.check()
        if winner:
            # Get the loser based on whether or not the winner is x's
            # If the winner is x's, the loser is o's...obviously, and vice-versa
            loser = board.challengers['x'] if board.challengers['x'] != winner else board.challengers['o']
            await self.bot.say("{} has won this game of TicTacToe, better luck next time {}".format(winner.display_name,
                                                                                                    loser.display_name))
            # Handle updating ratings based on the winner and loser
            update_records(winner, loser)
            # This game has ended, delete it so another one can be made
            del self.boards[ctx.message.server.id]
        else:
            # If no one has won, make sure the game is not full. If it has, delete the board and say it was a tie
            if board.full():
                await self.bot.say("This game has ended in a tie!")
                del self.boards[ctx.message.server.id]
            # If no one has won, and the game has not ended in a tie, print the new updated board
            # TODO: edit in place instead of printing?
            else:
                player_turn = board.challengers.get('x') if board.X_turn else board.challengers.get('o')
                fmt = str(board) + "\nIt is now your turn "
                await self.bot.say(str(board))

    @tictactoe.command(name='start', aliases=['challenge', 'create'], pass_context=True, no_pm=True)
    @checks.custom_perms(send_messages=True)
    async def start_game(self, ctx, player2: discord.Member):
        """Starts a game of tictactoe with another player"""
        player1 = ctx.message.author
        # For simplicities sake, only allow one game on a server at a time.
        # Things can easily get confusing (on the server's end) if we allow more than one
        if self.boards.get(ctx.message.server.id) is not None:
            await self.bot.say("Sorry but only one Tic-Tac-Toe game can be running per server!")
            return
        # Make sure we're not being challenged, I always win anyway
        if player2 == ctx.message.server.me:
            await self.bot.say("You want to play? Alright lets play.\n\nI win, so quick you didn't even notice it.")
            return
        # Create the board and return who has been decided to go first
        x_player = self.create(ctx.message.server.id, player1, player2)
        fmt = "A tictactoe game has just started between {} and {}".format(player1.display_name, player2.display_name)
        # Print the board too just because
        fmt += str(self.boards[ctx.message.server.id])
        # We don't need to do anything weird with assigning x_player to something, it is already a member object, just use it
        fmt += "I have decided at random, and {} is going to be x's this game. It is your turn first!\nUse the {}tictactoe command, and a position, to choose where you want to play".format(x_player.display_name, ctx.prefix)
        await self.bot.say(fmt)
    
    @tictactoe.command(name='delete', aliases=['stop', 'remove', 'end'], pass_context=True, no_pm=True)
    @checks.custom_perms(kick_members=True)
    async def stop_game(self, ctx):
        """Force stops a game of tictactoe
        This should realistically only be used in a situation like one player leaves
        Hopefully a moderator will not abuse it, but there's not much we can do to avoid that"""
        if self.boards.get(ctx.message.server.id) is None:
            await self.bot.say("There are no tictactoe games running on this server!")
            return
            
        del self.boards[ctx.message.server.id]
        await self.bot.say("I have just stopped the game of TicTacToe, a new should be able to be started now!")


def setup(bot):
    bot.add_cog(TicTacToe(bot))
