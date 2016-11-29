import discord
from discord.ext import commands
from .utils import checks

import random
import re
from enum import Enum


class Chess:
    def __init__(self, bot):
        self.bot = bot
        # Our format for games is going to be a little different, because we do want to allow multiple games per server
        # Format should be {'server_id': [Game, Game, Game]}
        self.games = {}

    def play(self, player, notation):
        """Our task to handle a player making their actual move"""
        game = self.get_game(player)

        # Check if the player is in a game
        if game is None:
            return MoveStatus.no_game

        # Check if it's this players turn
        if not game.can_play:
            return MoveStatus.wrong_turn

        if '0-0-0' in notation:
            # Set our piece to the rook, this is what we'll base the move off of
            colour = 'W' if game.white_turn else 'B'
            piece = '{}R'.format(colour)

            # Due to the weird way castling works when promoting a pawn, we just want to check the positioning
            if piece in game.board[7][0]:
                position = (7, 0)
            elif piece in game.board[0][0]:
                position = (0, 0)
            # If we're trying to castle a rook that's not in these two positions, this is invald
            else:
                return MoveStatus.invalid

            # Attempt to castle the rook provided
            if game.castle(position):
                return MoveStatus.valid
            else:
                return MoveStatus.invalid
        elif '0-0' in notation:
            # Set our piece to the rook, this is what we'll base the move off of
            colour = 'W' if game.white_turn else 'B'
            piece = '{}R'.format(colour)

            # Due to the weird way castling works when promoting a pawn, we just want to check the positioning
            if piece in game.board[0][7]:
                position = (0, 7)
            elif piece in game.board[7][7]:
                position = (7, 7)
            # If we're trying to castle a rook that's not in these two positions, this is invald
            else:
                return MoveStatus.invalid

            # Attempt to castle the rook provided
            if game.castle(position):
                return MoveStatus.valid
            else:
                return MoveStatus.invalid
        else:
            # Possible formats: e4, e4Q, e4=Q, Ng4d4
            try:
                # Check for the case when there are two peices who can move to the same position
                multi_move = re.search('(N|R|K|Q|P|B)([a-h][1-8])([a-h][1-8])', notation)
                piece = multi_move.group(1)
                original_pos = multi_move.group(2)
                new_pos = multi_move.group(3)
            except AttributeError:
                # Otherwise, we need the piece and position
                try:
                    piece = re.search('(king|queen|pawn|bishop|rook|bishop|knight)', notation.lower()).group(1)
                    position = re.search('[a-h][1-8]=?(Q|R|B|N)?', notation).group(0)

                    if len(position) > 2:
                        promotion = position[-1:]
                        position = position[:2]
                    else:
                        promotion = None
                    if game.move(piece, position.upper(), position):
                        return MoveStatus.valid
                    else:
                        return MoveStatus.invalid
                except IndexError:
                    return MoveStatus.invalid

    def get_game(self, player):
        """Provides the game this player is playing, in this server"""
        server_games = self.games.get(player.server.id, [])
        for game in server_games:
            if player in game.challengers.values():
                return game

        return None

    def in_game(self, player):
        """Checks to see if a player is playing in a game right now, in this server"""
        server_games = self.games.get(player.server.id, [])
        for game in server_games:
            if player in game.challengers.values():
                return True

        return False

    def start_game(self, player1, player2):
        game = Game(player1, player2)
        try:
            self.games[player1.server.id].append(game)
        except KeyError:
            self.games[player1.server.id] = [game]

        return game

    @commands.group(pass_contxt=True, invoke_without_command=True)
    @checks.custom_perms(send_messages=True)
    async def chess(self, ctx, *, move):
        """Moves a piece based on the notation provided
        Notation for normal moves are {piece} to {position} based on the algebraic notation of the board (This is on the picture)
        Example: Knight to d4; Rook to e2, etc.
        Special moves:
        - Castling
            - King side: Notation is: 0-0  (the letter o)
            - Queen side: Notation is: 0-0-0 (the letter o)
        - Promoting a pawn (when moving to the other end of the board, you can promote your pawn to a bishop, queen, knight, or rook):
            - {position}{piece to promote to} i.e. pawn to e8Q (to move the pawn to e8, and promote to a queen)
        - Taking a  piece:
            - Provide normal notation (i.e. rook to d4), this code will handle piece taking
        - En Passant:
            - Provide normal notation
        - If two pieces of the same rank can move to the same destination:
            - Review this first: https://en.wikipedia.org/wiki/Algebraic_notation_(chess)#Disambiguating_moves
            - For the sake of ease, we will only use #3 in our formatting. For example 'Knight to d4' when two of them can go there, should be provided exactly like 'Ng4d4' if the piece you want is on g4, and needs to move to d4. This is an invalid move, but is just for an example
        - Check/Checkmate
            - Provide normal notation

            EXAMPLE: !rook to d4"""
        result = self.play(ctx.message.author, move)
        if result is MoveStatus.invalid:
            await self.bot.say("That was an invalid move!")
        elif result is MoveStatus.wrong_turn:
            await self.bot.say("It is not your turn to play on your game in this server!")
        elif result is MoveStatus.no_game:
            await self.bot.say("You are not currently playing a game on this server!")
        elif result is MoveStatus.valid:
            game = self.get_game(ctx.message.author)
            link = game.draw_board()
            await self.bot.upload(link)

    @commands.command(pass_context=True)
    @checks.custom_perms(send_messages=True)
    async def chess_start(self, ctx, player2: discord.Member):
        """Starts a chess game with another player
        You can play one game on a single server at a time

        EXAMPLE: !chess start @Victim
        RESULT: A new chess game! Good luck~"""

        # Lets first check our permissions; we're not going to create a text based board
        # So we need to be able to attach files in order to send the board
        if not ctx.message.channel.permissions_for(ctx.message.server.me).attach_files:
            await self.bot.say(
                "I need to be able to send pictures to provide the board! Please ask someone with mange roles permission, to grant me attach files permission if you want to play this")
            return

        # Make sure the author and player 2 are not in a game already
        if self.in_game(ctx.message.author):
            await self.bot.say("Sorry, but you can only be in one game per server at a time")
            return

        if self.in_game(player2):
            await self.bot.say("Sorry, but {} is already in a game on this server!".format(player2.display_name))
            return

        # Start the game
        game = self.start_game(ctx.message.author, player2)
        player1 = game.challengers.get('white')
        await self.bot.say(
            "{} you have started a chess game with {}\n\n{} will be white this game, and is going first.\nIf you need information about the notation used to play, run {}help chess".format(
                ctx.message.author.display_name, player2.display_name, ctx.prefix))


class MoveStatus(Enum):
    invalid = 0
    valid = 1
    wrong_turn = 2
    no_game = 3
    invalid_promotion = 4


class Game:
    def __init__(self, player1, player2):

        # Randomize who goes first when the board is created
        if random.SystemRandom().randint(0, 1):
            self.challengers = {'white': player1, 'black': player2}
        else:
            self.challengers = {'white': player2, 'black': player1}

        # White goes first, so base whose turn it is off of that
        self.white_turn = True

        self.board = None
        self.reset_board()

        # The point of chess revolves around the king's position
        # Due to this, we're going to use the king's position a lot, so lets save this variable 
        self.w_king_pos = (0, 4)
        self.b_king_pos = (7, 4)

        # Now, there's a move called En Passant: https://en.wikipedia.org/wiki/En_passant
        # This can be done, if the piece being "taken" is in a specific position....and was just moved
        # The latter is why this is important here, lets save a variable for the last pawn moved
        self.last_pawn_moved = None

        # The other special case we can do is castling, if the rook and king have not been moved yet this can be done
        self.can_castle = {'white': {
            (0, 0): True,
            (0, 7): True},
            'black': {
                (7, 0): True,
                (7, 7): True}}

    def draw_board(self):
        """Create an image, and return the image link, based on self.board"""
        pass

    def reset_board(self):
        # Lets face the board with white on the bottom, black on top
        # Chess notation is {letter}{number} which a 2D array doesn't support
        # So we're just going to create this based on a normal number array
        # However, we're going to flip it to make the row part of notation easier
        self.board = [['WR', 'WN', 'WB', 'WQ', 'WK', 'WB', 'WN', 'WR'],
                      ['WP', 'WP', 'WP', 'WP', 'WP', 'WP', 'WP', 'WP'],
                      ['', '', '', '', '', '', '', ''],
                      ['', '', '', '', '', '', '', ''],
                      ['', '', '', '', '', '', '', ''],
                      ['', '', '', '', '', '', '', ''],
                      ['BP', 'BP', 'BP', 'BP', 'BP', 'BP', 'BP', 'BP'],
                      ['BR', 'BN', 'BB', 'BQ', 'BK', 'BB', 'BN', 'BR']]

    # We want to send a different message if it's not this players turn
    # So lets split up 'can_play' and the checks for that actual move
    def can_play(self, player):
        """Determined if it's this player's turn or not"""
        if self.white_turn:
            return player == self.challengers.get('white')
        elif not self.white_turn:
            return player == self.challengers.get('black')

    def castle(self, pos):
        # Lets get our king's position, and set our colour based on whose turn it is
        if self.white_turn:
            colour = 'white'
            king_pos = self.w_king_pos
        else:
            colour = 'black'
            king_pos = self.b_king_pos

        if not can_castle[colour][pos]:
            return False

        # During castling, the row should never change
        new_king_row = king_pos[0]
        # Change the column, based on the position. If the rook is in an invalid position
        # Which should be caught by the can_castle, but still lets make sure, just return False
        if pos[1] == 0:
            new_king_column = king_pos[1] - 2
        elif pos[1] == 7:
            new_king_column = king_pos[1] + 2
        else:
            return False
        new_king_pos = (new_king_row, new_king_column)

        # Lets now check, if it meets the condition "One may not castle out of, through, or into check"
        for column_pos in range(king_pos[1], new_king_column + 1):
            if not self._valid_king_move(king_pos, (king_pos[0], column_pos)):
                return False

        # Now lets check for the check state, if we're in check we cannot castle
        if self.check():
            return False

        # Now lets check if the rook can move to the required position, if not then we can't castle either
        new_rook_row = pos[0]
        if pos[1] == 0:
            new_rook_column = pos[1] + 3
        elif pos[1] == 7:
            new_rook_column = pos[1] - 2
        else:
            return False
        new_rook_pos = (new_rook_row, new_rook_column)
        if not self._valid_rook_move(pos, new_rook_pos):
            return False

        # Otherwise, we can castle, so lets move both pieces
        self._move(king_pos, new_king_pos)
        self._move(pos, new_rook_pos)
        # This is going to flip the turn twice, so lets flip it manually one more time
        self.white_turn = not self.white_turn
        return False

    def move(self, piece, pos, promotion=None):
        """Moves a piece to the provided position"""
        # First lets transform the position
        pos = (pos[1] - 1, ord(pos[0].upper()) - 65)

        # Now lets transform the piece to what it will be on the board
        piece_map = {'knight': 'N',
                     'king': 'K',
                     'bishop': 'B',
                     'queen': 'Q',
                     'rook': 'R',
                     'pawn': 'P'}

        piece_colour = 'W' if self.white_turn else 'B'
        piece = "{}{}".format(piece_colour, piece_map.get(piece))

        # Lets check for a piece that matches the provided one
        for x, row in enumerate(self.board):
            for y, board_piece in enumerate(row):
                if piece == board_piece:
                    # TODO: Handle when multiple pieces of the same type can move to the same position
                    # And they haven't provided the specific one
                    if self.valid_move((x, y), pos):
                        self._move(piece, (x, y), pos)

                        if promotion is not None:
                            piece = "{}{}".format(piece_colour, promotion)
                            self.board[pos[0]][pos[1]][1] = piece
                        return

    # Our internal method for actually moving the piece
    def _move(self, piece, pos, new_pos):
        # Set our last pawn moved to the new position if a pawn was moved
        # Otherwise it needs to be None
        if 'P' in piece:
            self.last_pawn_moved = new_pos
            # TODO: Check here for En Passant, to take the piece one position below
        else:
            self.last_pawn_moved = None

        # If the king has been moved, the player cannot castle anymore
        if 'K' in piece:
            if self.white_turn:
                colour = 'white'
                self.w_king_pos = new_pos
            else:
                colour = 'black'
                self.b_king_pos = new_pos

            for x in self.can_castle[colour]:
                self.can_castle[colour][x] = False

        # If the rook has been moved (depending on the side it was on)
        # Then that side cannot be moved anymore
        # Now, according to the rules, the following example is valid:
        # - Promote a pawn to a rook, in the queen's corner
        # - This rook has now not been moved, therefore it can be castled
        # So we need to be a little lenient here
        # This is why our castling "on or off" is based on position, so we can simply use that
        if 'R' in piece:
            colour = 'white' if self.white_turn else 'black'
            try:
                self.can_castle[colour][pos] = False
            except KeyError:
                pass

        # Now lets do the actual 'moving' of pieces
        # There's nothing special that happens we need to keep track of, when taking an enemy piece
        # So lets just overwrite it, that's it
        self.board[new_pos[0]][new_pos[1]] = piece
        self.board[pos[0]][pos[1]] = ''
        self.white_turn = not self.white_turn

    # Next couple methods are going to be used for convenience in order to check some things
    # The idea of how to check for a "Check" is:
    # - Get king position
    # - Get all pieces on the other team
    # - Check if their move, to ours, is a valid move
    # To do this we need the following convenience methods

    def check(self):
        """Checks our current board, and checks (based on whose turn it is) if we're in a 'check' state"""
        # To check for a check, what we should do is loop through the board
        # Then check if it's the the current players turn's piece, and compare to moving to the king's position 
        for x, row in enumerate(self.board):
            for y, piece in enumerate(row):
                if self.white_turn and re.search('B.', piece) and self.valid_move((x, y), self.b_king_pos):
                    return True
                elif not self.white_turn and 'W' in piece and self.valid_move((x, y), self.w_king_pos):
                    return True

    def checkmate(self):
        """Checks our current board, and checks (based on whose turn it is) if we're in a 'checkmate' state"""
        # We don't care about our check position, as this doesn't matter to us
        # We can be in chekcmate if we have no other pieces, or are in check
        # So calling check first is not something this method needs to worry about
        king_pos = self.w_king_pos if self.white_turn else self.b_king_pos

        # Lets do this dynamicaly, this is our range of movement (-1, 0, 1) for a king
        move_range = range(-1, 2)
        # Loop through the horizontal movements
        for x in move_range:
            # Loop through the vertical movements
            for y in move_range:
                # If we hit any position that we can move to, then we are not in checkmate
                if self._valid_king_move(king_pos, (x, y)):
                    return False

    def valid_move(self, pos, new_pos):
        """Determines if a move from pos to new_pos is valid"""
        # Lets make sure a valid position was given, if not then we obviously can't move that piece (it don't exist brah)
        try:
            piece = self.board[pos[0]][pos[1]]
        except IndexError:
            return False
        try:
            new_piece = self.board[new_pos[0]][new_pos[1]]
        except IndexError:
            return False

        # First and easiest check, make sure this is their piece
        if self.white_turn and 'W' not in piece:
            return False
        elif not self.white_turn and not re.search('B.', piece):
            return False

        # Another easy check, no pieces can move onto their own piece
        # This will also inadvertantly check if new_pos == pos
        if self.white_turn and 'W' in new_piece:
            return False
        elif not self.white_turn and re.search('B.', new_piece):
            return False

        # Now lets check based on the type of piece it is, if they can move to the new position
        # If the piece is a pawn
        if 'P' in piece:
            return self._valid_pawn_move(pos, new_pos, piece, new_piece)
        # If the piece is a rook
        elif 'R' in piece:
            return self._valid_rook_move(pos, new_pos)
        # If the piece is a Bishop (since there are "B" for black pieces, we need to check the second position)
        # We're not going to use splicing here, in case this is a blank spot
        elif re.search('(W|B)B', piece):
            return self._valid_bishop_move(pos, new_pos)
        # If the piece was a knight
        elif 'N' in piece:
            return self._valid_knight_move(pos, new_pos)
        # If the piece was the queen
        elif 'Q' in piece:
            # The queen can move like a rook, or bishop, so return true if either of these are met
            return any((self._valid_rook_move(pos, new_pos), self._valid_bishop_move(pos, new_pos)))
        # If the piece was the king
        elif 'K' in piece:
            return self._valid_king_move(pos, new_pos)
        # Otherwise this isn't a real piece, of course you can't move it
        else:
            return False

    def _valid_king_move(self, pos, new_pos):
        # The movement is simple, can move in any direction but only once
        # However, we need to ensure this wouldn't be put us into check
        x_movement = abs(new_pos[1] - pos[1])
        y_movement = abs(new_pos[0] - pos[0])
        if x_movement > 1 or y_movement > 1:
            return False

        # Now we can check for the check
        for x, row in enumerate(self.board):
            for y, piece in enumerate(row):
                if self.white_turn and re.search('B.', piece) and self.valid_pos((x, y), new_pos):
                    return False
                elif not self.white_turn and 'W' in piece and self.valid_pos((x, y), new_pos):
                    return False

        # If this wouldn't cause check, then it's valid
        return True

    def _valid_knight_move(self, pos, new_pos):
        # This is pretty simple, the knight can skip over pieces
        # So we need to just check if the L shape it can make
        x_movement = abs(new_pos[1] - pos[1])
        y_movement = abs(new_pos[0] - pos[0])

        if x_movement == 2:
            return y_movement == 1
        elif y_movement == 2:
            return x_movement == 1

    def _valid_bishop_move(self, pos, new_pos):
        # We can only move in diagonals, easiest way to check this:
        # Make sure we're moving the same amount in both directions
        if new_pos[0] - pos[0] != new_pos[1] - new_pos[1]:
            return False
        # We also cannot jump over other pieces, so lets check this as well
        increment_x = 1 if new_pos[0] > pos[0] else -1
        increment_y = 1 if new_pos[1] > pos[1] else -1

        temp_pos = pos
        while temp_pos != new_pos:
            if self.board[temp_pos[0]][temp_pos[1]] != '':
                return False
            temp_pos[0] += increment_x
            temp_pos[1] += increment_y

        return True

    def _valid_pawn_move(self, pos, new_pos, piece, new_piece):
        num_paces = new_pos[0] - pos[0] if self.white_turn else pos[0] - new_pos[0]

        # The pawn has a lot of odd limitations compared to the rest of the pieces
        # The easiest way to check this is going to be to check the limitations

        # Lets first check if we're moving straight forward
        if new_pos[1] == pos[1]:
            # Easiest check if we're moving straight forward, we cannot take another piece by this method, period
            if new_piece != '':
                return False

            # Now let's check if it's outside the range of what can possibly be moved in a straight line (2 paces)
            if num_paces not in [1, 2]:
                return False

            # Now check if we're moving twice
            if num_paces == 2:
                # If we are moving twice, we have to be on home row
                if (self.white_turn and pos[0] != 1) or (not self.white_turn and pos[0] != 6):
                    return False

                # We cannot hop over a piece, make sure there's nothing in between us
                if (self.white_turn and self.board[2][new_pos[1]] != '') or (
                    not self.white_turn and self.board[5][new_pos[1]] != ''):
                    return False
        # If these checks are not met, then our move is valid
        else:
            # Now lets check if we are moving diagonally one column first
            # Since if we're not moving in a straight line, that's the only other possiblity

            # Since we based num_paces earlier, off of whether or not this is a white/black piece
            # We can only need to check here if it's moving 'forward' 1 pace (== 1)
            if num_paces != 1:
                return False
            if abs(new_pos[1] - pos[1]) != 1:
                return False

            # En Passant is going to be a bit more complicated, so for now lets just check if there's an enemy piece where we're moving
            if self.white_turn:
                if not re.search('B.', new_piece):
                    # TODO: Check En Passant: https://en.wikipedia.org/wiki/En_passant
                    return False
            else:
                if 'W' not in new_piece:
                    # TODO: Check En Passant: https://en.wikipedia.org/wiki/En_passant
                    return False
        # If we have passed all these checks, then this is a valid move
        return True

    def _valid_rook_move(self, pos, new_pos):
        # We can only move in straight lines, so we require at least one of these below to not be hit
        if pos[0] != new_pos[0] and pos[1] != new_pos[1]:
            return False
        # Next we need to check if there are any pieces in between the piece and the new position
        # To do this, loop through the range between the current and new positions
        if pos[0] == new_pos[0]:
            increment_var = 1 if new_pos[1] > pos[1] else -1
            for i in range(pos[1], new_pos[1]):
                if self.board[pos[0]][i] != '':
                    return False
        else:
            increment_var = 1 if new_pos[0] > pos[0] else -1
            for i in range(pos[0], new_pos[0]):
                if self.board[i][pos[1]] != '':
                    return False
        return True


def setup(bot):
    bot.add_cog(Chess(bot))
