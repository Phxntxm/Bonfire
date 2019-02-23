import asyncio
import discord

import utils
from utils import Deck, Suit, Face
from discord.ext import commands


card_map = {
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
    "10": "ten"
}


class Player:
    def __init__(self, member, game):
        self.discord_member = member
        self.game = game
        self.channel = member.dm_channel
        if self.channel is None:
            loop = asyncio.get_event_loop()
            loop.create_task(self.set_channel())
        self.hand_message = None
        self.table_message = None
        self.hand = Deck(prefill=False, spades_high=True)
        self.bid = 0
        self.points = 0
        self.tricks = 0

        self.played_card = None

        self._messages_to_clean = []

    @property
    def bid_num(self):
        if self.bid == "moon":
            return 13
        elif self.bid == "nil":
            return 0
        return self.bid

    async def send_message(self, content=None, embed=None, delete=True):
        """A convenience method to send the message to the player, then add it to the list of messages to delete"""
        _msg = await self.discord_member.send(content, embed=embed)
        if delete:
            self._messages_to_clean.append(_msg)
        return _msg

    async def set_channel(self):
        self.channel = await self.discord_member.create_dm()

    async def show_hand(self):
        embed = discord.Embed(title="Hand")
        diamonds = []
        hearts = []
        clubs = []
        spades = []

        for card in sorted(self.hand):
            if card.suit == Suit.diamonds:
                diamonds.append(str(card.face_short))
            if card.suit == Suit.hearts:
                hearts.append(str(card.face_short))
            if card.suit == Suit.clubs:
                clubs.append(str(card.face_short))
            if card.suit == Suit.spades:
                spades.append(str(card.face_short))

        if diamonds:
            embed.add_field(name="Diamonds", value=", ".join(diamonds), inline=False)
        if hearts:
            embed.add_field(name="Hearts", value=", ".join(hearts), inline=False)
        if clubs:
            embed.add_field(name="Clubs", value=", ".join(clubs), inline=False)
        if spades:
            embed.add_field(name="Spades", value=", ".join(spades), inline=False)

        if self.hand_message:
            await self.hand_message.edit(embed=embed)
        else:
            self.hand_message = await self.discord_member.send(embed=embed)

    async def show_table(self):

        embed = discord.Embed(title="Table")

        if self.game.round.suit:
            embed.add_field(name="Round suit", value=self.game.round.suit.name, inline=False)
        else:
            embed.add_field(name="Round suit", value=self.game.round.suit, inline=False)

        winning_card = self.game.round.winning_card
        if winning_card:
            embed.add_field(name="Winning card", value=str(winning_card), inline=False)

        for num, p in enumerate(self.game.players):
            fmt = "{} ({}/{} tricks): {}".format(
                p.discord_member.display_name,
                p.tricks,
                p.bid_num,
                p.played_card
            )
            embed.add_field(name="Player {}".format(num + 1), value=fmt, inline=False)

        if self.table_message:
            await self.table_message.edit(embed=embed)
        else:
            self.table_message = await self.discord_member.send(embed=embed)

    async def get_bid(self):
        await self.send_message(
            content="It is your turn to bid. Please provide 1-12, nil, or moon depending on the bid you want. "
            "Please note you have 3 minutes to bid, any longer and you will be removed from the game.")
        self.bid = 0

        def check(m):
            possible = ['nil', 'moon', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']
            return m.channel == self.channel \
                and m.author.id == self.discord_member.id \
                and m.content.strip().lower() in possible

        msg = await self.game.bot.wait_for('message', check=check)
        content = msg.content.strip().lower()
        if content == '0':
            self.bid = 'nil'
        elif content == '13':
            self.bid = 'moon'
        elif content.isdigit():
            self.bid = int(content)
        else:
            self.bid = content
        await self.send_message(content="Thank you for your bid! Please wait while I get the other players' bids...")
        return self.bid

    async def play(self):
        fmt = "It is your turn to play, provide your response in the form '[value] of [face]' such as Ace of Spades. "
        fmt += "Your hand can be found above when you bid earlier."

        await self.send_message(content=fmt)
        await self.game.bot.wait_for('message', check=self.play_check)
        await self.send_message(content="You have played...please wait for the other players")

    async def clean_messages(self):
        for msg in self._messages_to_clean:
            await msg.delete()

        self._messages_to_clean = []

    def play_check(self, message):
        if message.channel != self.channel or message.author.id != message.author.id:
            return False
        if " of " not in message.content:
            return False
        try:
            parts = message.content.partition('of')
            face = parts[0].split()[-1].lower()
            suit = parts[2].split()[0].lower()
            face = card_map.get(face, face)

            suit = getattr(Suit, suit)
            face = getattr(Face, face)

            card = self.hand.get_card(suit, face)
            if card is not None and self.game.round.can_play(self, card):
                self.played_card = card
                self.hand.pluck(card=card)

                return True
            else:
                return False
        except (IndexError, AttributeError):
            return False

    def score(self):
        if self.bid == 'nil':
            if self.tricks == 0:
                self.points += 100
            else:
                self.points -= 100
        elif self.bid == 'moon':
            if self.tricks == 13:
                self.points += 200
            else:
                self.points -= 200
        else:
            if self.tricks >= self.bid:
                self.points += self.bid * 10
                self.points += self.tricks - self.bid
            else:
                self.points -= self.bid * 10

        self.bid = 0
        self.tricks = 0

    def has_suit(self, face):
        for card in self.hand:
            if face == card.suit:
                return True
        return False

    def has_only_spades(self):
        for card in self.hand:
            if card.suit != Suit.spades:
                return False

        return True


class Round:
    def __init__(self):
        self.spades_broken = False
        self.cards = Deck(prefill=False, spades_high=True)
        self.suit = None

    def can_play(self, player, card):
        if self.cards.count == 0:
            if card.suit != Suit.spades:
                return True
            else:
                return self.spades_broken or player.has_only_spades()
        else:
            if card.suit == self.suit:
                return True
            else:
                return not player.has_suit(self.suit)

    def play(self, card):
        # Set the suit
        if self.cards.count == 0:
            self.suit = card.suit
        # This will override the deck, and set it to the round's deck (this is what we want)
        card.deck = self.cards
        self.cards.insert(card)
        if card.suit == Suit.spades:
            self.spades_broken = True

    @property
    def winning_card(self):
        cards = sorted([
            card
            for card in self.cards
            if card.suit == self.suit or card.suit == Suit.spades], reverse=True
        )
        try:
            return cards[0]
        except IndexError:
            return None

    def reset(self):
        list(self.cards.draw(count=self.cards.count))
        self.suit = None


class Game:
    def __init__(self, bot):
        self.bot = bot
        self.players = []
        self.deck = Deck(spades_high=True)
        self.deck.shuffle()
        self.round = Round()
        self.started = False
        self.card_count = 13
        self.score_limit = 250

    async def start(self):
        self.started = True
        special_bids = ['nil', 'moon', 'misdeal']
        fmt = "All 4 players have joined, and your game of Spades has started!\n"
        fmt += "Rules for this game can be found here: https://www.pagat.com/boston/spades.html. "
        fmt += "Special actions/bids allowed are: `{}`\n".format(", ".join(special_bids))
        fmt += "Players are:\n" + "\n".join(p.discord_member.display_name for p in self.players)
        fmt += "\n\nPlease wait while all players bid...then the first round will begin"
        for p in self.players:
            await p.discord_member.send(fmt)

        await self.game_task()

    async def game_task(self):
        winner = None
        # some while loop, while no one has won yet
        while winner is None:
            await self.play_round()
            winner = self.get_winner()
            await self.new_round()

    async def play_round(self):
        # For clarities sake, I want to send when it starts, immediately
        # then follow through with the hand and betting when it's their turn
        self.deal()
        for p in self.players:
            await p.show_hand()
            await p.show_table()
            await p.get_bid()

        self.order_turns(self.get_highest_bidder())

        # Bids are complete, time to start the game
        await self.clean_messages()

        fmt = "Alright, everyone has bid, the bids are:\n{}".format(
            "\n".join("{}: {}".format(p.discord_member.display_name, p.bid) for p in self.players))
        for p in self.players:
            await p.send_message(content=fmt)

        # Once bids are done, we can play the actual round
        for i in range(self.card_count):
            # Wait for each player to play
            for p in self.players:
                await p.play()
                self.round.play(p.played_card)
                # Update everyone's table once each person has finished
                await self.update_table()
            # Get the winner after the round, increase their tricks
            winner = self.get_round_winner()
            winning_card = winner.played_card
            winner.tricks += 1
            # Order players based off the winner
            self.order_turns(winner)

            # Reset the round
            await self.reset_round()
            fmt = "{} won with a {}".format(winner.discord_member.display_name, winning_card)
            for p in self.players:
                await p.send_message(content=fmt)

    async def update_table(self):
        for p in self.players:
            await p.show_table()

    async def clean_messages(self):
        for p in self.players:
            await p.clean_messages()

    async def reset_round(self):
        self.round.reset()
        await self.clean_messages()
        # First loop through to set everyone's card to None
        for p in self.players:
            p.played_card = None
        # Now we can show the table correctly, since everyone's card is set correctly
        for p in self.players:
            await p.show_hand()
            await p.show_table()

    def get_highest_bidder(self):
        highest_bid = -1
        highest_player = None
        for player in self.players:
            print(player.bid_num, player.discord_member.display_name)
            if player.bid_num > highest_bid:
                highest_player = player

        print(highest_player.discord_member.display_name)

        return highest_player

    def order_turns(self, player):
        index = self.players.index(player)
        self.players = self.players[index:] + self.players[:index]

    def get_round_winner(self):
        winning_card = self.round.winning_card
        for p in self.players:
            if winning_card == p.played_card:
                return p

    def get_winner(self):
        for p in self.players:
            if p.points >= self.score_limit:
                return p

    async def new_round(self):
        score_msg = discord.Embed(title="Table scores")
        for p in self.players:
            p.score()
            p.played_card = None
            p.hand_message = None
            p.table_message = None
            score_msg.add_field(
                name="Player {}".format(p.discord_member.display_name),
                value="{}/{}".format(p.points, self.score_limit),
                inline=False
            )

        # We should do this after scoring, so a separate loop is needed here for that
        for p in self.players:
            await p.send_message(embed=score_msg)

        # Round the round's reset information (this is the one run after each round of cards...this won't do everything)
        self.round.reset()
        # This is the only extra thing needed to fully reset the round itself
        self.round.spades_broken = False
        # Set the deck back and shuffle it
        self.deck.refresh()
        self.deck.shuffle()
        # This is all we want to do here, this is just preparing for the new round...not actually starting it

    def deal(self):
        for _ in range(self.card_count):
            for p in self.players:
                card = list(self.deck.draw())
                p.hand.insert(card)

    def join(self, member):
        p = Player(member, self)
        self.players.append(p)


class Spades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_game = None
        self.games = []

    def get_game(self, member):
        # Simply loop through each game's players, find the one that matches and return it
        for g, _ in self.games:
            for p in g.players:
                if member.id == p.discord_member.id:
                    return g
        if self.pending_game:
            for p in self.pending_game.players:
                if member.id == p.discord_member.id:
                    return self.pending_game

    def join_game(self, author):
        # First check if there's a pending game
        if self.pending_game:
            # If so add the player to it
            self.pending_game.join(author)
            # If we've hit 4 players, we want to start the game, add it to our list of games, and wipe our pending game
            if len(self.pending_game.players) == 2:
                task = self.bot.loop.create_task(self.pending_game.start())
                self.games.append((self.pending_game, task))
                self.pending_game = None
        # If there's no pending game, start a pending game
        else:
            g = Game(self.bot)
            g.join(author)
            self.pending_game = g

    def cog_unload(self):
        # Simply cancel every task
        for _, task in self.games:
            task.cancel()

    @commands.command()
    @utils.can_run(send_messages=True)
    async def spades(self, ctx):
        """Used to join a spades games. This can be used in servers, or in PM, however it will be handled purely via PM.
        There are no teams in this version of spades, and blind nil/moon bids are not allowed. The way this is handled
        is for each person joining, there is a pending game ready to start...once 4 people have joined the "lobby" the
        game will start.

        EXAMPLE: !spades
        RESULT: You've joined the spades lobby!"""
        author = ctx.message.author
        game = self.get_game(author)
        if game:
            if game.started:
                await ctx.send("You are already in a game! Check your PM's if you are confused")
            else:
                await ctx.send("There are {} players in your lobby".format(len(game.players)))
            return
        # Before we add the player to the game, we need to ensure we can PM this user
        # So lets do this backwards, confirm the user has joined the game, *then* join the game
        try:
            await author.send("You have joined a spades lobby! Please wait for more people to join, "
                              "before the game can start")
            if ctx.guild:
                await ctx.send("Check your PM's {}. I have sent you information about your spades lobby".format(
                    author.display_name))
            self.join_game(author)
        except discord.Forbidden:
            await ctx.send("This game is ran through PM's only! "
                           "Please enable your PM's on this server if you want to play!")


def setup(bot):
    bot.add_cog(Spades(bot))
