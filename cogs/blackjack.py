from . import utils

from discord.ext import commands

import asyncio
import math

face_map = {
    'S': 'spades',
    'D': 'diamonds',
    'C': 'clubs',
    'H': 'hearts'
}

card_map = {
    'A': 'Ace',
    'K': 'King',
    'Q': 'Queen',
    'J': 'Jack'
}


class Blackjack:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    def __unload(self):
        # Simply cancel every task
        for game in self.games.values():
            game.task.cancel()

    def create_game(self, message):
        # When we're done with the game, we need to delete the game itself and remove it's instance from games
        # To do this, it needs to be able to access this instance of Blackjack
        game = Game(self.bot, message, self)
        self.games[message.server.id] = game

    @commands.group(pass_context=True, no_pm=True, aliases=['bj'], invoke_without_command=True)
    @utils.custom_perms(send_messages=True)
    async def blackjack(self, ctx):
        """Creates a game/joins the current running game of blackjack

        EXAMPLE: !blackjack
        RESULT: A new game of blackjack!"""
        # Get this server's game if it exists
        game = self.games.get(ctx.message.server.id)
        # If it doesn't, start one
        if game is None:
            self.create_game(ctx.message)
        else:
            # Try to join the game
            status = game.join(ctx.message.author)
            # If it worked, they're ready to play
            if status:
                fmt = "{} has joined the game of blackjack, and will be able to play next round!"
                await self.bot.say(fmt.format(ctx.message.author.display_name))
            else:
                # Otherwise, lets check *why* they couldn't join
                if game.playing(ctx.message.author):
                    await self.bot.say("You are already playing! Wait for your turn!")
                else:
                    await self.bot.say("There are already a max number of players playing/waiting to play!")

    @blackjack.command(pass_context=True, no_pm=True, name='leave', aliases=['quit'])
    @utils.custom_perms(send_messages=True)
    async def blackjack_leave(self, ctx):
        """Leaves the current game of blackjack

        EXAMPLE: !blackjack leave
        RESULT: You stop losing money in blackjack"""

        # Get this server's game if it exists
        game = self.games.get(ctx.message.server.id)

        if game is None:
            await self.bot.say("There are currently no games of Blackjack running!")
            return

        status = game.leave(ctx.message.author)
        if status:
            await self.bot.say("You have left the game, and will be removed at the end of this round")
        else:
            await self.bot.say("Either you have already bet, or you are not even playing right now!")

    @blackjack.command(pass_context=True, no_pm=True, name='forcestop', aliases=['stop'])
    @utils.custom_perms(manage_server=True)
    async def blackjack_stop(self, ctx):
        """Forces the game to stop, mostly for use if someone has gone afk

        EXAMPLE: !blackjack forcestop
        RESULT: No more blackjack spam"""

        # Get this server's game if it exists
        game = self.games.get(ctx.message.server.id)

        if game is None:
            await self.bot.say("There are currently no games of Blackjack running!")
            return

        game.task.cancel()
        del self.games[ctx.message.server.id]
        await self.bot.say("The blackjack game running here has just ended")


def FOIL(a, b):
    """Uses FOIL to calculate a new possible total (who knew math would come in handy?!)

    For our purposes, we are adding, not multiplying, so this is not the *same* as using normal FOIL
    So no built in method will work"""

    # This whole thing may *look* like it may add a lot of entries
    # However, we are going to be using pretty short lists, and duplicate entries will be common
    # So this isn't actually as bad as it looks
    new_totals = []
    for i in a:
        for x in b:
            total = i + x
            if total not in new_totals:
                new_totals.append(total)

    # The list comprehension is to ensure we don't care about totals over 21
    new_totals = [x for x in new_totals if x < 22]
    return new_totals


class Player:
    def __init__(self, member):
        self.member = member
        self.hand = utils.Deck(prefill=False)

        # The chips a player starts with
        self.chips = 1000

    @property
    def bust(self):
        for total in self.count:
            if total <= 21:
                return False
        return True

    @property
    def count(self):
        """The current count of our hand"""
        total = [0]

        for card in self.hand:
            # Order is suit, face...so we want the second value
            face = card[1]

            if face in ['Q', 'K', 'J']:
                for index, t in enumerate(total):
                    total[index] += 10
            elif face == 'A':
                total = FOIL(total, [1, 11])
            else:
                for index, t in enumerate(total):
                    total[index] += int(face)

        # If we have more than one possible total (there is at least one ace) then we do not care about one if it is
        # over 21
        if len(total) > 1:
            new_total = [x for x in total if x < 22]
            # However, if the ace is there and both possibilities cause a bust, we want the lowest one to be our count
            if len(new_total) == 0:
                new_total = [min(total)]
            total = new_total

        return total

    def __eq__(self, other):
        if isinstance(other, Player):
            if hasattr(other, 'member') and other.member == self.member:
                return True
        return False

    def __str__(self):
        # We only care about our hand, for printing wise
        fmt = "Hand:\n"
        fmt += "\n".join(
            "{} of {}".format(
                card_map.get(card[1], card[1]),
                face_map.get(card[0], card[0]))
            for card in self.hand
        )
        fmt += "\n(Total: {})".format(self.count)
        return fmt


class Game:
    def __init__(self, bot, message, bj):
        player = Player(message.author)
        self.bj = bj
        self.bot = bot
        self.players = [{'status': 'playing', 'player': player}]
        # Our buffer for players who want to join
        # People cannot join in the middle of a game, so we'll add them at the end
        self._added_players = []
        # Our list of players who lost/left
        self._removed_players = []

        # The channel we'll send messages to
        self.channel = message.channel

        # People can join in on this game, but lets make sure we don't go over the limit however
        self._max_players = 10

        # Lets create our main deck, and shuffle it
        self.deck = utils.Deck()
        # So apparently, it is possible, with 10 players and nearly everyone/everyone busting
        # To actually deplete the deck, and cause it to return None, and mess up later
        # Due to this, lets make put 2 decks in here
        _deck2 = utils.Deck()
        self.deck.insert(list(_deck2.draw(52)))
        del _deck2
        self.deck.shuffle()
        # The dealer
        self.dealer = Player('Dealer')

        self.min_bet = 5
        self.max_bet = 500
        self.bet = 0

        self.task = self.bot.loop.create_task(self.game_task())

    async def game_task(self):
        """The task to handle the entire game"""
        while len(self.players) > 0:
            await self.bot.send_message(self.channel, "A new round has started!!")

            # First wait for bets
            await self.bet_task()
            # To allow people to leave correctly during the betting phase
            # (i.e. they left before they bet) we need to do a cleanup here
            self.player_cleanup()

            # Then deal to every player
            self.deal()
            # Now wait for our round to finish
            await self.round_task()
            # Now it's the dealers turn
            # This is the only loop we have to worry about still occurring if there are no more players
            # This is due to the fact the dealer has nothing to do with players during his "turn"
            # We need an extra check here to stop this from occurring
            if len(self.players) > 0:
                await self.dealer_task()
            # Then clean everything up, including:
            # Put everyone's hand inside the deck
            # Shuffle the deck
            # Payout/pickup bets
            # Include any new players
            # Remove players leaving/ran out of chips
            await self.cleanup()

        # If we reach the end of this loop, that means there are no more players
        del self.bj.games[self.channel.server.id]

    async def dealer_task(self):
        """The task handling the dealer's play after all players have stood"""
        fmt = "It is the dealer's turn to play\n\n{}".format(self.dealer)
        msg = await self.bot.send_message(self.channel, fmt)

        while True:
            await asyncio.sleep(1)
            if self.dealer.bust:
                fmt = msg.content + "\n\nDealer has busted!!"
                await self.bot.edit_message(msg, fmt)
                return
            for num in self.dealer.count:
                if num > 16:
                    return
            self.hit(self.dealer)
            fmt = "It is the dealer's turn to play\n\n{}".format(self.dealer)
            msg = await self.bot.edit_message(msg, fmt)

    async def round_task(self):
        """The task handling the round itself, asking each person to hit or stand"""
        # This task is going to be called at the beginning of a game
        # It is purely for asking for hit or stand from each player, till this round is over
        # A differen task will handle if a player hit blackjack to start (so they would not be 'playing')

        # Our check to make sure a valid 'command' was provided
        check = lambda m: m.content.lower() in ['hit', 'stand', 'double']

        # First lets handle the blackjacks
        for entry in [p for p in self.players if p['status'] == 'blackjack']:
            player = entry['player']
            fmt = "You got a blackjack {0.member.mention}!\n\n{0}".format(player)

            await self.bot.send_message(self.channel, fmt)
        # Loop through each player (as long as their status is playing) and they have bet chips
        for entry in [p for p in self.players if p['status'] == 'playing' and hasattr(p['player'], 'bet')]:
            player = entry['player']

            # Let them know it's their turn to play
            fmt = "It is your turn to play {0.member.mention}\n\n{0}".format(player)
            await self.bot.send_message(self.channel, fmt)

            # If they're not playing anymore (i.e. they busted, are standing, etc.) then we don't want to keep asking
            #  them to hit or stand
            while entry['status'] not in ['stand', 'bust']:

                # Ask if they want to hit or stand
                fmt = "Hit, stand, or double?"
                await self.bot.send_message(self.channel, fmt)
                msg = await self.bot.wait_for_message(timeout=60, author=player.member, channel=self.channel,
                                                      check=check)

                # If they took to long, make them stand so the next person can play
                if msg is None:
                    await self.bot.send_message(self.channel, "Took to long! You're standing!")
                    entry['status'] = 'stand'
                # If they want to hit
                elif 'hit' in msg.content.lower():
                    self.hit(player)
                    await self.bot.send_message(self.channel, player)
                # If they want to stand
                elif 'stand' in msg.content.lower():
                    self.stand(player)
                elif 'double' in msg.content.lower():
                    self.double(player)
                    await self.bot.send_message(self.channel, player)
                    # TODO: Handle double, split

    async def bet_task(self):
        """Performs the task of betting"""

        def check(_msg):
            """Makes sure the  message provided is within the min and max bets"""
            try:
                msg_length = int(_msg.content)
                return self.min_bet <= msg_length <= self.max_bet
            except ValueError:
                return _msg.content.lower() == 'skip'

        # There is one situation that we want to allow that means we cannot loop through players like normally would
        # be the case: Betting has started; while one person is betting, another joins This means our list has
        # changed, and neither based on the length or looping through the list itself will handle this To handle
        # this, we'll loop 'infinitely', get a list of players who haven't bet yet, and then use the first person in
        # that list
        while True:
            players = [p for p in self.players if p['status'] == 'playing']

            # If everyone has bet/there is no one playing anymore
            if len(players) == 0:
                break

            entry = players[0]
            player = entry['player']

            fmt = "Your turn to bet {0.member.mention}, your current chips are: {0.chips}\n" \
                  "Current min bet is {1}, current max bet is {2}\n" \
                  "Place your bet now (please provide only the number;" \
                  "'skip' if you would like to leave this game)".format(player, self.min_bet, self.max_bet)
            await self.bot.send_message(self.channel, fmt)
            msg = await self.bot.wait_for_message(timeout=60, author=player.member, channel=self.channel, check=check)

            if msg is None:
                await self.bot.send_message(self.channel, "You took too long! You're sitting this round out")
                entry['status'] = 'stand'
            elif msg.content.lower() == 'skip':
                await self.bot.send_message(self.channel, "Alright, you've been removed from the game")
                self.leave(player.member)
            else:
                num = int(msg.content)
                # Set the new bet, and remove it from this players chip total
                if num <= player.chips:
                    player.bet = num
                    player.chips -= num
                    entry['status'] = 'bet'
                else:
                    await self.bot.send_message(self.channel, "You can't bet more than you have!!")
            # Call this so that we can correct the list, if someone has left or join
            self.player_cleanup()

    async def cleanup(self):
        """Performs the tasks done after the game has completed"""
        dealer_count = max(self.dealer.count)

        # A list of losers, winners, and people who tied
        losers = []
        ties = []
        winners = []
        blackjack = []

        for entry in self.players:
            player = entry['player']
            # Quick check here to ensure the player isn't someone who got added
            # Specifically right after the betting phase
            if not hasattr(player, 'bet'):
                continue

            hand = player.hand
            count = max(player.count)

            # First, lets handle bets
            # TODO: Handle blackjacks
            # First if is to check If we can possibly win (a bust is an automatic loss, no matter what)
            # Payouts for wins are 2 times the bet
            if entry['status'] == 'blackjack':
                if dealer_count != 21:
                    player.chips += math.floor(player.bet * 2.5)
                    blackjack.append(player)
                else:
                    # A push, the player gets their chips back
                    player.chips += player.bet
                    ties.append(player)
            elif not player.bust:
                # If the dealer busts, we win
                if dealer_count > 21:
                    player.chips += player.bet * 2
                    winners.append(player)
                else:
                    # If the dealer hasn't busted, we need to compare
                    if count == dealer_count:
                        # A push, the player gets their chips back
                        player.chips += player.bet
                        ties.append(player)
                    elif count > dealer_count:
                        # The player won, they get their payout
                        player.chips += player.bet * 2
                        winners.append(player)
                    else:
                        # The player lost
                        losers.append(player)
            else:
                # Otherwise, they lost, nothing we need to do
                losers.append(player)

            player.bet = 0

            # "Draw" the remaining cards so that the hand is emptied, as well as returned
            cards = list(hand.draw(hand.count))
            # Now add them back into the deck
            self.deck.insert(cards)

            # While we're already looping, another task we need to complete is removing people who lost
            # So if their chips are 0 (or less which shouldn't happen) add them to the _removed_players list
            if player.chips <= 0:
                self._removed_players.append(player)

            entry['status'] = 'playing'

        # Now that we've looped through everyone, send the message regarding the outcome
        fmt = "Round stats:\n"
        if len(winners) > 0:
            # First get a string of all the winners
            _fmt = " ".join(m.member.display_name for m in winners)
            # Add that to the main string
            fmt += "Winners: {}\n".format(_fmt)
        if len(losers) > 0:
            # First get a string of all the losers
            _fmt = " ".join(m.member.display_name for m in losers)
            # Add that to the main string
            fmt += "Losers: {}\n".format(_fmt)
        if len(ties) > 0:
            # First get a string of all the ties
            _fmt = " ".join(m.member.display_name for m in ties)
            # Add that to the main string
            fmt += "Ties: {}\n".format(_fmt)
        if len(blackjack) > 0:
            # First get a string of all the blackjacks
            _fmt = " ".join(m.member.display_name for m in blackjack)
            # Add that to the main string
            fmt += "Blackjacks: {}\n".format(_fmt)

        await self.bot.send_message(self.channel, fmt)

        # Do the same for the dealers hand
        cards = list(self.dealer.hand.draw(self.dealer.hand.count))
        self.deck.insert(cards)
        self.player_cleanup()
        # Now that's complete, shuffle the deck
        self.deck.shuffle()

    def player_cleanup(self):
        """Handles the cleanup of adding and removing waiting players"""
        # We need this method separate from our other cleanup processes
        # Because people can leave/join in the middle of betting (if they haven't already bet)
        # Include the new players
        self.players.extend(self._added_players)
        self._added_players.clear()

        # What we want to do is remove any players that are in the game and have left the server
        for entry in self.players:
            m = entry['player'].member
            if m not in self.channel.server.members:
                self._removed_players.append(entry['player'])

        # Remove the players who left
        self.players = [p for p in self.players if p['player'] not in self._removed_players]
        self._removed_players.clear()

    def _get_player_index(self, player):
        """Provides the index of a certain player"""
        for i, entry in enumerate(self.players):
            if entry['player'] == player:
                return i

    def get_player(self, member):
        """Returns the player object for the discord member provided"""
        for entry in self.players:
            if entry['player'].member == member:
                return entry['player']

    def playing(self, member):
        """Returns true if the member provided is currently in this game"""
        for entry in self.players:
            if member == entry['player'].member:
                return True
        return False

    def deal(self):
        """Deals to all players playing"""

        # I would like this to simulate a real "deal", so need to deal to each member in order
        for i in range(2):
            for entry in self.players:
                card = list(self.deck.draw())
                entry['player'].hand.insert(card)

                # Make sure we detect blackjack here, as this is when it matters
                if 21 in entry['player'].count:
                    entry['status'] = 'blackjack'
                else:
                    entry['status'] = 'playing'
            # Also add a card to the dealer's hand
            card = list(self.deck.draw())
            self.dealer.hand.insert(card)

    def join(self, member):
        """Adds the member to the game playing"""
        if self.playing(member):
            return False
        if len(self.players) + len(self._added_players) >= self._max_players:
            return False
        player = Player(member)
        entry = {'status': 'playing', 'player': player}
        self._added_players.append(entry)
        return True

    def leave(self, member):
        player = self.get_player(member)
        # If they are playing, then add them to the _removed_players list so that they can be removed at the end of
        # the round
        if player:
            # We need to make sure they haven't already bet
            index = self._get_player_index(player)
            if self.players[index]['status'] == 'bet':
                return False
            else:
                self.players[index]['status'] = 'left'
                self._removed_players.append(player)
                return True
        else:
            return False

    def double(self, player):
        """Doubles down on the current hand"""
        # First double the bet
        player.chips -= player.bet
        player.bet *= 2
        # Then hit
        self.hit(player)
        # After doubling down, they are not allowed to play again, make them stand
        self.stand(player)

    def stand(self, player):
        """Causes a player to stand"""
        for entry in self.players:
            if entry['player'] == player:
                entry['status'] = 'stand'
                return

    def hit(self, player):
        """Hits a player"""
        # Draw one card
        card = list(self.deck.draw())
        # Add it to the player's hand
        player.hand.insert(card)

        # If this is the dealer, we don't need to care about this
        if player == self.dealer:
            return

        if player.bust:
            index = self._get_player_index(player)
            self.players[index]['status'] = 'bust'
        elif 21 in player.count:
            index = self._get_player_index(player)
            self.players[index]['status'] = 'stand'


def setup(bot):
    bot.add_cog(Blackjack(bot))
