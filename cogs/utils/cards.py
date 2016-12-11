import itertools
import random

suits = ['S', 'C', 'H', 'D']
faces = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']

class Deck:
    def __init__(self, prefill=True):
        # itertools.product creates us a tuple based on every output of our faces and suits
        # This is EXACTLY what a deck of normal playing cards is, so it's perfect
        if prefill:
            self.deck = list(itertools.product(suits, faces))

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

    def shuffle(self):
        """Shuffles the deck in place"""
        random.SystemRandom().shuffle(self.deck)
