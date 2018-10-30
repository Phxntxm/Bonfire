import random

from enum import IntEnum, auto


class Suit(IntEnum):
    clubs = auto()
    hearts = auto()
    diamonds = auto()
    spades = auto()


class Face(IntEnum):
    ace = auto()
    two = auto()
    three = auto()
    four = auto()
    five = auto()
    six = auto()
    seven = auto()
    eight = auto()
    nine = auto()
    ten = auto()
    jack = auto()
    queen = auto()
    king = auto()


class Deck:
    def __init__(self, prefill=True, ace_high=True, spades_high=False):
        self.deck = []
        if prefill:
            self.refresh()

        self.ace_high = ace_high
        self.spades_high = spades_high

    def __iter__(self):
        for card in self.deck:
            yield card

    def __getitem__(self, key):
        return self.deck[key]

    def refresh(self):
        """A method that 'restarts' the deck, filling it back with 52 cards"""
        self.deck = []

        for _suit in Suit:
            for _face in Face:
                self.insert(Card(_suit, _face, self))

    @property
    def count(self):
        """A property to provide how many cards are currently in the deck"""
        return len(self.deck)

    @property
    def empty(self):
        """A property to determine whether or not the deck has cards in it"""
        return len(self.deck) == 0

    def draw(self, count=1):
        """Generator to draw from the deck"""
        try:
            for i in range(count):
                yield self.deck.pop()
        except IndexError:
            yield None

    def insert(self, cards):
        """Adds the provided cards to the end of the deck"""
        try:
            self.deck.extend(cards)
            for card in cards:
                card._deck = self
        except TypeError:
            self.deck.append(cards)
            cards._deck = self

    def index(self, card):
        """Returns the index of the card provided (-1 if card is not in the deck)"""
        return self.deck.index(card)

    def pluck(self, index=None, card=None):
        """Pulls the provided card from the deck"""
        if index:
            return self.deck.pop(index)
        elif card:
            return self.deck.pop(self.index(card))

    def shuffle(self):
        """Shuffles the deck in place"""
        random.SystemRandom().shuffle(self.deck)

    def get_card(self, suit, face):
        """Returns the provided card in the deck"""
        for card in self.deck:
            if card.suit == suit and card.value == face:
                return card


class Card:
    """The class that holds all the details for a card in the deck"""

    def __init__(self, suit, value, deck):
        self._suit = suit
        self._value = value
        self._deck = deck

    @property
    def suit(self):
        """The suit (club, diamond, heart, spade)"""
        return self._suit

    @property
    def value(self):
        """The face value (2-10, J, Q, K, A)"""
        return self._value

    @property
    def face_short(self):
        """The first 'letter' of the face, (2-10 will be the numbers)"""
        if self.value == Face.ace or \
           self.value == Face.jack or \
           self.value == Face.queen or \
           self.value == Face.king:
            return self.value.name[0]
        else:
            return self.value.value

    def __hash__(self):
        return self.value.value + len(Face) * (self.suit.value - 1)

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.suit == other.suit and self.value == other.value

    def __ne__(self, other):
        if not isinstance(other, Card):
            return True
        return not self.__eq__(other)

    def __str__(self):
        return "%s of %s" % (self.value.name, self.suit.name)

    def __lt__(self, other):
        if self._deck.spades_high:
            if other.suit == Suit.spades and self.suit != Suit.spades:
                return True
            if self.suit == Suit.spades and other.suit != Suit.spades:
                return False

        self_value = self.value.value
        other_value = other.value.value

        if self._deck.ace_high:
            if self.value == Face.ace:
                self_value = 14
            if other.value == Face.ace:
                other_value = 14

        return self_value < other_value

    def __gt__(self, other):
        if self._deck.spades_high:
            if other.suit == Suit.spades and self.suit != Suit.spades:
                return False
            if self.suit == Suit.spades and other.suit != Suit.spades:
                return True

        self_value = self.value.value
        other_value = other.value.value

        if self._deck.ace_high:
            if self.value == Face.ace:
                self_value = 14
            if other.value == Face.ace:
                other_value = 14

        return self_value > other_value

    def __le__(self, other):
        return self.__eq__(other) or self.__lt__(other)

    def __ge__(self, other):
        return self.__eq__(other) or self.__gt__(other)
