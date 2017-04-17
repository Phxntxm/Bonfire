import itertools
import random
from functools import cmp_to_key

suits = ['S', 'C', 'H', 'D']
faces = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

class Deck:
    def __init__(self, prefill=True):
        # itertools.product creates us a tuple based on every output of our faces and suits
        # This is EXACTLY what a deck of normal playing cards is, so it's perfect
        if prefill:
            self.deck = list(itertools.product(suits, faces))
        else:
            self.deck = []

    def __iter__(self):
        for card in self.deck:
            yield card

    def refresh(self):
        """A method that 'restarts' the deck, filling it back with 52 cards"""
        self.deck = list(itertools.product(suits, faces))

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
        self.deck.extend(cards)

    def pluck(self, card):
        """Pulls the provided card from the deck"""
        return self.deck.pop(self.deck.index(card))

    def shuffle(self):
        """Shuffles the deck in place"""
        random.SystemRandom().shuffle(self.deck)

    def sorted_deck(self):
        """Provides a sorted representation of the current deck"""
        # The idea behind this one is for being useful in hands...there's no reason we need to sort in place
        # So all we're going to do here is compare how we want, and return the sorted representation
        def compare(first, second):
            if suits.index(first[0]) < suits.index(second[0]):
                return -1
            elif suits.index(first[0]) > suits.index(second[0]):
                return 1
            else:
                if faces.index(first[1]) < faces.index(second[1]):
                    return -1
                elif faces.index(first[1]) > faces.index(second[1]):
                    return 1
                else:
                    return 0

        return sorted(self.deck, key=cmp_to_key(compare))
